from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.database import Database
from app.web.schemas import EpisodeSummaryResponse, JobResponse
from app.web.security import redact_secrets


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebRepository:
    def __init__(self, database: Database, output_root: Path):
        self.database = database
        self.output_root = output_root

    def create_job(
        self,
        job_type: str,
        episode_id: str | None,
        idempotency_key: str,
        scene_number: int | None = None,
        staging_directory: str | None = None,
    ) -> JobResponse:
        now = _now()
        job_id = f"webjob_{uuid4().hex}"
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO web_generation_jobs (
                        job_id, episode_id, job_type, scene_number, status,
                        current_stage, progress_percent, idempotency_key,
                        created_at, updated_at, staging_directory
                    ) VALUES (?, ?, ?, ?, 'queued', 'queued', 0, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        episode_id,
                        job_type,
                        scene_number,
                        idempotency_key,
                        now,
                        now,
                        staging_directory,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError(
                "An active or duplicate job already exists for this episode."
            ) from exc
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobResponse:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_generation_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Web job not found: {job_id}")
        return self._job_response(dict(row))

    def recent_jobs(self, limit: int = 20) -> list[JobResponse]:
        safe_limit = max(1, min(limit, 100))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM web_generation_jobs
                ORDER BY created_at DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._job_response(dict(row)) for row in rows]

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        stage: str,
        progress: int,
        error: str | None = None,
        archive_directory: str | None = None,
    ) -> None:
        now = _now()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE web_generation_jobs
                SET status = ?, current_stage = ?, progress_percent = ?,
                    error_message = ?, updated_at = ?,
                    started_at = CASE
                        WHEN started_at IS NULL AND ? = 'running' THEN ?
                        ELSE started_at END,
                    completed_at = CASE
                        WHEN ? IN ('completed','failed','interrupted',
                                   'waiting_for_approval') THEN ?
                        ELSE completed_at END,
                    archive_directory = COALESCE(?, archive_directory)
                WHERE job_id = ?
                """,
                (
                    status,
                    stage,
                    progress,
                    error,
                    now,
                    status,
                    now,
                    status,
                    now,
                    archive_directory,
                    job_id,
                ),
            )

    def bind_job_episode(self, job_id: str, episode_id: str) -> None:
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    UPDATE web_generation_jobs
                    SET episode_id = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (episode_id, _now(), job_id),
                )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError(
                "Another active job already exists for this episode."
            ) from exc

    def recover_interrupted_jobs(self) -> int:
        now = _now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE web_generation_jobs
                SET status = 'interrupted',
                    current_stage = 'interrupted',
                    error_message =
                        'Application stopped before the job completed.',
                    completed_at = ?,
                    updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (now, now),
            )
        return cursor.rowcount

    def approve(self, episode_id: str) -> None:
        now = _now()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE episodes
                SET approval_status = 'approved', approved_at = ?,
                    rejection_reason = NULL, rejected_at = NULL,
                    upload_status = 'not_ready'
                WHERE episode_id = ?
                """,
                (now, episode_id),
            )

    def episode_exists(self, episode_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM episodes WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
        return row is not None

    def reject(self, episode_id: str, reason: str) -> None:
        now = _now()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE episodes
                SET approval_status = 'rejected', rejection_reason = ?,
                    rejected_at = ?, approved_at = NULL,
                    upload_status = 'not_ready'
                WHERE episode_id = ?
                """,
                (reason, now, episode_id),
            )

    def list_episodes(self, status_filter: str = "all") -> list[EpisodeSummaryResponse]:
        clauses = {
            "completed": "e.generation_status = 'completed'",
            "failed": "e.generation_status = 'failed'",
            "waiting": "e.approval_status = 'pending' AND e.generation_status = 'completed'",
            "approved": "e.approval_status = 'approved'",
            "rejected": "e.approval_status = 'rejected'",
        }
        where = clauses.get(status_filter)
        query = """
            SELECT e.*, COALESCE(q.passed, 0) AS quality_passed
            FROM episodes e
            LEFT JOIN quality_reports q ON q.episode_id = e.episode_id
        """
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY e.creation_date DESC"
        with self.database.connect() as connection:
            rows = connection.execute(query).fetchall()
        return [self._summary(dict(row)) for row in rows]

    def dashboard_counts(self) -> dict[str, int]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(1) AS total,
                    SUM(CASE WHEN generation_status='completed' THEN 1 ELSE 0 END)
                        AS completed,
                    SUM(CASE WHEN generation_status='completed'
                              AND approval_status='pending' THEN 1 ELSE 0 END)
                        AS waiting,
                    SUM(CASE WHEN generation_status='failed' THEN 1 ELSE 0 END)
                        AS failed
                FROM episodes
                """
            ).fetchone()
        return {key: int(row[key] or 0) for key in row.keys()}

    def assets(self, episode_id: str) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT scene_number, asset_type, provider, file_path, status,
                       created_at
                FROM assets WHERE episode_id = ?
                ORDER BY asset_type, scene_number
                """,
                (episode_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_assets_deleted(self, episode_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE assets SET status = 'deleted'
                WHERE episode_id = ?
                  AND asset_type NOT IN ('story', 'metadata',
                                         'character_bible')
                """,
                (episode_id,),
            )

    def archive_asset_paths(
        self,
        episode_id: str,
        mappings: dict[str, str],
    ) -> None:
        with self.database.connect() as connection:
            for old_path, archive_path in mappings.items():
                connection.execute(
                    """
                    UPDATE assets
                    SET file_path = ?, status = 'archived'
                    WHERE episode_id = ? AND file_path = ?
                      AND status != 'archived'
                    """,
                    (archive_path, episode_id, old_path),
                )

    def mark_media_deleted(self, episode_id: str) -> None:
        self.mark_assets_deleted(episode_id)
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE episodes
                SET final_video_path = NULL,
                    generation_status = 'story_ready',
                    approval_status = 'pending',
                    upload_status = 'not_ready'
                WHERE episode_id = ?
                """,
                (episode_id,),
            )

    def _summary(self, row: dict) -> EpisodeSummaryResponse:
        episode_dir = self.output_root / row["episode_id"]
        story = _read_json(episode_dir / "story.json")
        return EpisodeSummaryResponse(
            episode_id=row["episode_id"],
            title=str(story.get("title", row["episode_id"])),
            category=row["story_category"],
            main_character=row["main_character_type"],
            duration=int(row["duration"]),
            creation_date=row["creation_date"],
            generation_status=row.get("generation_status", "story_ready"),
            approval_status=row["approval_status"],
            upload_status=row["upload_status"],
            providers=json.loads(row["providers_used"] or "{}"),
            final_video_exists=(episode_dir / "final_short.mp4").is_file(),
            quality_status=(
                "passed" if int(row.get("quality_passed", 0)) else "not_ready"
            ),
        )

    @staticmethod
    def _job_response(row: dict) -> JobResponse:
        if row.get("error_message"):
            row["error_message"] = redact_secrets(row["error_message"])
        return JobResponse.model_validate(row)


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
