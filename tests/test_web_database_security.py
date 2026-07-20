from pathlib import Path

import pytest
from fastapi import HTTPException

from app.database import Database
from app.web.repository import WebRepository
from app.web.security import (
    redact_secrets,
    safe_media_path,
    validate_episode_id,
    validate_scene_number,
)


def test_web_migration_and_duplicate_active_job(tmp_path: Path):
    database = Database(tmp_path / "panel.db")
    database.initialize()
    repository = WebRepository(database, tmp_path / "output")
    first = repository.create_job("generate", None, "new-story-1")

    assert first.status == "queued"
    with database.connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(web_generation_jobs)"
            )
        }
    assert {"progress_percent", "staging_directory", "retry_count"} <= columns


def test_path_traversal_and_input_validation(tmp_path: Path):
    with pytest.raises(HTTPException):
        safe_media_path(tmp_path, "episode_0001", "../secret.env")
    with pytest.raises(HTTPException):
        validate_episode_id("../../bad")
    with pytest.raises(HTTPException):
        validate_scene_number(7)
    safe = safe_media_path(
        tmp_path, "episode_0001", "clips/scene_01.mp4"
    )
    assert safe.is_relative_to((tmp_path / "episode_0001").resolve())


def test_log_secret_redaction():
    value = redact_secrets(
        "OPENAI_API_KEY=secret-value Authorization: Bearer abc123"
    )

    assert "secret-value" not in value
    assert "abc123" not in value
    assert value.count("***REDACTED***") == 2


def test_recent_job_errors_are_redacted(tmp_path: Path):
    database = Database(tmp_path / "panel.db")
    database.initialize()
    repository = WebRepository(database, tmp_path / "output")
    job = repository.create_job("generate", None, "redaction-job")
    repository.update_job(
        job.job_id,
        status="failed",
        stage="failed",
        progress=100,
        error="OPENAI_API_KEY=do-not-show",
    )

    visible = repository.recent_jobs()[0]

    assert "do-not-show" not in str(visible.error_message)
    assert "***REDACTED***" in str(visible.error_message)
