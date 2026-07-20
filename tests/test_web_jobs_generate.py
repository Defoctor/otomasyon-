from pathlib import Path
import time

from fastapi.testclient import TestClient

from app.web import create_web_app
from app.web.job_manager import JobManager
from tests.test_web_app import web_settings
from tests.test_web_pages_media import seed_episode


def wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(100):
        response = client.get(f"/jobs/{job_id}")
        data = response.json()
        if data["status"] not in {"queued", "running"}:
            return data
        time.sleep(0.01)
    raise AssertionError("Job did not finish.")


def test_generate_endpoint_runs_in_background_and_reports_progress(
    tmp_path: Path,
):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    stages = []

    def handler(job_id, job_type, payload, progress):
        stages.append(job_type)
        progress("generating_images", 25)
        progress("quality_check", 95)
        return "episode_0001"

    def factory(settings, repository):
        return JobManager(settings, repository, work_handler=handler)

    application = create_web_app(settings, job_manager_factory=factory)
    with TestClient(application) as client:
        response = client.post(
            "/episodes/generate",
            json={
                "create_story": False,
                "episode_id": "episode_0001",
                "automatic_category": True,
                "duration_seconds": 30,
            },
        )
        assert response.status_code == 202
        completed = wait_for_job(client, response.json()["job_id"])

    assert stages == ["generate"]
    assert completed["status"] == "waiting_for_approval"
    assert completed["progress_percent"] == 100


def test_duplicate_active_episode_job_is_blocked(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    blocker = __import__("threading").Event()

    def handler(job_id, job_type, payload, progress):
        blocker.wait(timeout=2)
        return "episode_0001"

    def factory(settings, repository):
        return JobManager(settings, repository, work_handler=handler)

    application = create_web_app(settings, job_manager_factory=factory)
    payload = {
        "create_story": False,
        "episode_id": "episode_0001",
        "automatic_category": True,
        "duration_seconds": 30,
    }
    with TestClient(application) as client:
        first = client.post("/episodes/generate", json=payload)
        second = client.post("/episodes/generate", json=payload)
        blocker.set()

    assert first.status_code == 202
    assert second.status_code == 409


def test_identical_request_is_allowed_after_previous_job_finishes(
    tmp_path: Path,
):
    settings = web_settings(tmp_path)
    seed_episode(settings)

    def handler(job_id, job_type, payload, progress):
        return "episode_0001"

    def factory(settings, repository):
        return JobManager(settings, repository, work_handler=handler)

    application = create_web_app(settings, job_manager_factory=factory)
    payload = {
        "create_story": False,
        "episode_id": "episode_0001",
        "automatic_category": True,
        "duration_seconds": 30,
    }
    with TestClient(application) as client:
        first = client.post("/episodes/generate", json=payload)
        first_result = wait_for_job(client, first.json()["job_id"])
        second = client.post("/episodes/generate", json=payload)
        second_result = wait_for_job(client, second.json()["job_id"])

    assert first_result["status"] == "waiting_for_approval"
    assert second.status_code == 202
    assert second_result["status"] == "waiting_for_approval"
    assert first_result["job_id"] != second_result["job_id"]


def test_startup_marks_running_jobs_interrupted(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    from app.database import Database
    from app.web.repository import WebRepository

    database = Database(settings.database_path)
    database.initialize()
    repository = WebRepository(database, settings.output_dir)
    job = repository.create_job(
        "regenerate_full", "episode_0001", "recovery-test"
    )
    repository.update_job(
        job.job_id,
        status="running",
        stage="rendering_video",
        progress=80,
    )

    application = create_web_app(settings)
    with TestClient(application) as client:
        recovered = client.get(f"/jobs/{job.job_id}").json()

    assert recovered["status"] == "interrupted"
    assert "stopped" in recovered["error_message"]


def test_startup_recovers_legacy_pending_job(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    from app.database import Database

    database = Database(settings.database_path)
    database.initialize()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO web_generation_jobs (
                job_id, episode_id, job_type, status, current_stage,
                progress_percent, idempotency_key, created_at, updated_at
            ) VALUES (
                'webjob_legacy_pending', 'episode_0001', 'generate',
                'pending', 'pending', 0, 'legacy-pending-key',
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )

    application = create_web_app(settings)
    with TestClient(application) as client:
        recovered = client.get("/jobs/webjob_legacy_pending").json()

    assert recovered["status"] == "interrupted"
    assert "pending" in recovered["error_message"].lower()


def test_panel_propagates_explicit_and_empty_seed(tmp_path: Path):
    settings = web_settings(tmp_path)
    payloads = []

    def handler(job_id, job_type, payload, progress):
        payloads.append(payload)
        return None

    def factory(settings, repository):
        return JobManager(settings, repository, work_handler=handler)

    application = create_web_app(settings, job_manager_factory=factory)
    base = {
        "create_story": True,
        "automatic_category": False,
        "category": "animal_rescue",
        "duration_seconds": 30,
    }
    with TestClient(application) as client:
        explicit = client.post(
            "/episodes/generate", json={**base, "seed": 918273}
        )
        wait_for_job(client, explicit.json()["job_id"])
        empty = client.post("/episodes/generate", json={**base, "seed": None})
        wait_for_job(client, empty.json()["job_id"])

    assert payloads[0]["seed"] == 918273
    assert payloads[1]["seed"] is None
