from datetime import datetime, timezone
import json
import sqlite3
from typing import Any
from uuid import uuid4

from app.database.connection import Database
from app.schemas.story import Story


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EpisodeRepository:
    def __init__(self, database: Database):
        self.database = database

    def next_episode_id(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(CAST(SUBSTR(episode_id, 9) AS INTEGER)) AS maximum
                FROM episodes
                WHERE episode_id GLOB 'episode_[0-9]*'
                """
            ).fetchone()
        next_number = int(row["maximum"] or 0) + 1
        return f"episode_{next_number:04d}"

    def save_story(
        self,
        story: Story,
        story_json_path: str,
        provider_name: str,
        idempotency_key: str,
    ) -> str:
        created_at = utc_now()
        job_id = f"job_{uuid4().hex}"
        character = story.character_bible.main_character
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT episode_id FROM generation_jobs
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing:
                return str(existing["episode_id"])

            connection.execute(
                """
                INSERT INTO episodes (
                    episode_id, creation_date, story_category,
                    main_character_type, character_description, hook_type,
                    ending_type, duration, providers_used,
                    generation_cost_estimate, approval_status, upload_status,
                    story_json_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'pending',
                          'not_ready', ?)
                """,
                (
                    story.episode_id,
                    created_at,
                    story.story_category.value,
                    character.species,
                    json.dumps(
                        character.model_dump(mode="json"), ensure_ascii=False
                    ),
                    story.hook_type,
                    story.ending_type,
                    story.duration_target_seconds,
                    json.dumps({"story": provider_name}),
                    story_json_path,
                ),
            )
            connection.execute(
                """
                INSERT INTO characters (
                    character_id, episode_id, species, description_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    character.character_id,
                    story.episode_id,
                    character.species,
                    json.dumps(
                        character.model_dump(mode="json"), ensure_ascii=False
                    ),
                    created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO scenes (
                    episode_id, scene_number, duration_seconds, narration,
                    visual_prompt, motion_prompt, emotion
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        story.episode_id,
                        scene.scene_number,
                        scene.duration_seconds,
                        scene.narration,
                        scene.visual_prompt,
                        scene.motion_prompt,
                        scene.emotion,
                    )
                    for scene in story.scenes
                ],
            )
            connection.execute(
                """
                INSERT INTO generation_jobs (
                    job_id, episode_id, status, current_stage, error_message,
                    idempotency_key, created_at, updated_at
                ) VALUES (?, ?, 'completed', 'story_saved', NULL, ?, ?, ?)
                """,
                (
                    job_id,
                    story.episode_id,
                    idempotency_key,
                    created_at,
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO story_experiments (
                    episode_id, story_category, character_type, hook_type,
                    ending_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    story.episode_id,
                    story.story_category.value,
                    character.species,
                    story.hook_type,
                    story.ending_type,
                    created_at,
                ),
            )
        return story.episode_id

    def record_failure(
        self,
        episode_id: str,
        idempotency_key: str,
        error_message: str,
    ) -> None:
        """Record failures when an episode row already exists."""
        now = utc_now()
        with self.database.connect() as connection:
            episode_exists = connection.execute(
                "SELECT 1 FROM episodes WHERE episode_id = ?", (episode_id,)
            ).fetchone()
            if not episode_exists:
                return
            connection.execute(
                """
                INSERT INTO generation_jobs (
                    job_id, episode_id, status, current_stage, error_message,
                    idempotency_key, created_at, updated_at
                ) VALUES (?, ?, 'failed', 'story_generation', ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO UPDATE SET
                    status = 'failed',
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                (
                    f"job_{uuid4().hex}",
                    episode_id,
                    error_message,
                    idempotency_key,
                    now,
                    now,
                ),
            )

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM episodes WHERE episode_id = ?", (episode_id,)
            ).fetchone()
        return dict(row) if row else None

    def latest_episode_id(self) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT episode_id FROM episodes
                ORDER BY CAST(SUBSTR(episode_id, 9) AS INTEGER) DESC
                LIMIT 1
                """
            ).fetchone()
        return str(row["episode_id"]) if row else None

    def table_names(self) -> set[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        return {str(row["name"]) for row in rows}

    def start_stage_two(self, episode_id: str) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE episodes
                SET generation_status = 'running'
                WHERE episode_id = ?
                """,
                (episode_id,),
            )
            connection.execute(
                """
                UPDATE generation_jobs
                SET status = 'running',
                    current_stage = 'stage2_rendering',
                    error_message = NULL,
                    updated_at = ?
                WHERE episode_id = ?
                """,
                (now, episode_id),
            )

    def record_asset(
        self,
        episode_id: str,
        asset_type: str,
        provider: str,
        file_path: str,
        scene_number: int | None = None,
        status: str = "completed",
    ) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM assets
                WHERE episode_id = ? AND asset_type = ?
                  AND file_path = ?
                """,
                (episode_id, asset_type, file_path),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE assets
                    SET provider = ?, scene_number = ?, status = ?,
                        created_at = ?
                    WHERE id = ?
                    """,
                    (
                        provider,
                        scene_number,
                        status,
                        now,
                        existing["id"],
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO assets (
                        episode_id, scene_number, asset_type, provider,
                        file_path, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode_id,
                        scene_number,
                        asset_type,
                        provider,
                        file_path,
                        status,
                        now,
                    ),
                )

    def complete_stage_two(
        self,
        episode_id: str,
        final_video_path: str,
        report_path: str,
        providers: dict[str, str],
    ) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT providers_used FROM episodes WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            current = json.loads(row["providers_used"]) if row else {}
            current.update(providers)
            connection.execute(
                """
                UPDATE episodes
                SET final_video_path = ?,
                    generation_status = 'completed',
                    providers_used = ?,
                    generation_cost_estimate = 0,
                    approval_status = 'pending',
                    upload_status = 'not_ready'
                WHERE episode_id = ?
                """,
                (
                    final_video_path,
                    json.dumps(current, ensure_ascii=False),
                    episode_id,
                ),
            )
            connection.execute(
                """
                UPDATE generation_jobs
                SET status = 'completed',
                    current_stage = 'quality_passed',
                    error_message = NULL,
                    updated_at = ?
                WHERE episode_id = ?
                """,
                (now, episode_id),
            )
            connection.execute(
                """
                INSERT INTO quality_reports (
                    episode_id, report_path, passed, confidence_score,
                    created_at
                ) VALUES (?, ?, 1, 1.0, ?)
                ON CONFLICT(episode_id) DO UPDATE SET
                    report_path = excluded.report_path,
                    passed = 1,
                    confidence_score = 1.0,
                    created_at = excluded.created_at
                """,
                (episode_id, report_path, now),
            )

    def fail_stage_two(self, episode_id: str, error_message: str) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE episodes
                SET generation_status = 'failed',
                    approval_status = 'pending',
                    upload_status = 'not_ready'
                WHERE episode_id = ?
                """,
                (episode_id,),
            )
            connection.execute(
                """
                UPDATE generation_jobs
                SET status = 'failed',
                    current_stage = 'stage2_failed',
                    error_message = ?,
                    updated_at = ?
                WHERE episode_id = ?
                """,
                (error_message, now, episode_id),
            )
