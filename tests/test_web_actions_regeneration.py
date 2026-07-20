import hashlib
from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient

from app.database import Database
from app.services.regeneration import RegenerationService
from app.web import create_web_app
from app.web.job_manager import JobManager
from app.web.repository import WebRepository
from tests.test_web_app import web_settings
from tests.test_web_jobs_generate import wait_for_job
from tests.test_web_pages_media import seed_episode


def test_approve_and_reject_keep_upload_not_ready(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    application = create_web_app(settings)

    with TestClient(application) as client:
        approved = client.post("/episodes/episode_0001/approve")
        rejected = client.post(
            "/episodes/episode_0001/reject",
            json={"reason": "Subtitle timing needs review."},
        )

    assert approved.status_code == 200
    assert approved.json()["upload_status"] == "not_ready"
    assert rejected.status_code == 200
    assert rejected.json()["approval_status"] == "rejected"
    database = Database(settings.database_path)
    with database.connect() as connection:
        row = connection.execute(
            """
            SELECT approval_status, upload_status, rejection_reason
            FROM episodes WHERE episode_id='episode_0001'
            """
        ).fetchone()
    assert row["approval_status"] == "rejected"
    assert row["upload_status"] == "not_ready"
    assert "timing" in row["rejection_reason"]


def test_regenerate_endpoints_create_separate_jobs(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    seen = []

    def handler(job_id, job_type, payload, progress):
        seen.append((job_type, payload))
        return "episode_0001"

    def factory(settings, repository):
        return JobManager(settings, repository, work_handler=handler)

    application = create_web_app(settings, job_manager_factory=factory)
    with TestClient(application) as client:
        full = client.post("/episodes/episode_0001/regenerate")
        full_job = wait_for_job(client, full.json()["job_id"])
        scene = client.post(
            "/episodes/episode_0001/scenes/3/regenerate"
        )
        scene_job = wait_for_job(client, scene.json()["job_id"])
        invalid = client.post(
            "/episodes/episode_0001/scenes/7/regenerate"
        )

    assert full.status_code == 202
    assert scene.status_code == 202
    assert full_job["job_type"] == "regenerate_full"
    assert scene_job["scene_number"] == 3
    assert invalid.status_code == 422
    assert [item[0] for item in seen] == [
        "regenerate_full",
        "regenerate_scene",
    ]


def test_staging_promotion_preserves_unselected_scene_hashes(tmp_path: Path):
    active = tmp_path / "episode_0001"
    staging = tmp_path / "staging" / "episode_0001"
    archive = tmp_path / "archive"
    for root in (active, staging):
        (root / "images").mkdir(parents=True)
        (root / "clips").mkdir(parents=True)
        for number in range(1, 7):
            for folder, extension in (("images", "png"), ("clips", "mp4")):
                value = f"same-{number}-{folder}".encode()
                if root == staging and number == 3:
                    value = f"new-{number}-{folder}".encode()
                (root / folder / f"scene_{number:02d}.{extension}").write_bytes(
                    value
                )
        (root / "final_short.mp4").write_bytes(
            b"old-final" if root == active else b"new-final"
        )
        (root / "quality_report.json").write_bytes(
            b"old-report" if root == active else b"new-report"
        )
    before = {
        number: _combined_hash(active, number) for number in range(1, 7)
    }

    RegenerationService._promote_selected(
        active,
        staging,
        archive,
        [
            "images/scene_03.png",
            "clips/scene_03.mp4",
            "final_short.mp4",
            "quality_report.json",
        ],
    )
    after = {
        number: _combined_hash(active, number) for number in range(1, 7)
    }

    assert before[3] != after[3]
    assert all(before[n] == after[n] for n in (1, 2, 4, 5, 6))
    assert (archive / "images" / "scene_03.png").is_file()
    assert (archive / "final_short.mp4").read_bytes() == b"old-final"


def test_delete_requires_confirmation_and_preserves_story_files(
    tmp_path: Path,
):
    settings = web_settings(tmp_path)
    directory = seed_episode(settings)
    for folder in ("images", "clips", "audio", "subtitles"):
        (directory / folder).mkdir()
        (directory / folder / "asset.bin").write_bytes(b"x")
    (directory / "final_short.mp4").write_bytes(b"video")
    (directory / "quality_report.json").write_text("{}", encoding="utf-8")
    application = create_web_app(settings)

    with TestClient(application) as client:
        denied = client.post(
            "/episodes/episode_0001/media/delete",
            json={"confirmation": "NO"},
        )
        assert (directory / "final_short.mp4").is_file()
        allowed = client.post(
            "/episodes/episode_0001/media/delete",
            json={"confirmation": "DELETE_MEDIA"},
        )

    assert denied.status_code == 422
    assert allowed.status_code == 200
    assert all(
        (directory / name).is_file()
        for name in ("story.json", "character_bible.json", "metadata.json")
    )
    assert not (directory / "final_short.mp4").exists()
    assert not (directory / "images").exists()


def test_mutating_unknown_episode_returns_404(tmp_path: Path):
    settings = web_settings(tmp_path)
    application = create_web_app(settings)

    with TestClient(application) as client:
        approve = client.post("/episodes/episode_9999/approve")
        regenerate = client.post("/episodes/episode_9999/regenerate")
        delete = client.post(
            "/episodes/episode_9999/media/delete",
            json={"confirmation": "DELETE_MEDIA"},
        )

    assert approve.status_code == 404
    assert regenerate.status_code == 404
    assert delete.status_code == 404


def test_startup_recovery_moves_incomplete_staging(tmp_path: Path):
    settings = web_settings(tmp_path)
    staging_job = settings.output_dir / ".staging" / "webjob_incomplete"
    staging_job.mkdir(parents=True)
    (staging_job / "partial.tmp").write_bytes(b"incomplete")
    database = Database(settings.database_path)
    database.initialize()
    repository = WebRepository(database, settings.output_dir)
    service = RegenerationService(settings, repository)

    recovered = service.recover_staging()

    assert recovered == ["webjob_incomplete"]
    assert not staging_job.exists()
    assert (
        settings.output_dir
        / ".interrupted"
        / "webjob_incomplete"
        / "partial.tmp"
    ).is_file()


def _combined_hash(root: Path, number: int) -> str:
    digest = hashlib.sha256()
    digest.update((root / "images" / f"scene_{number:02d}.png").read_bytes())
    digest.update((root / "clips" / f"scene_{number:02d}.mp4").read_bytes())
    return digest.hexdigest()
