from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.web import create_web_app


def web_settings(tmp_path: Path, host: str = "127.0.0.1") -> Settings:
    return Settings(
        app_env="test",
        log_level="INFO",
        demo_mode=True,
        story_provider="mock",
        output_dir=tmp_path / "output",
        database_path=tmp_path / "data" / "kids_shorts.db",
        default_language="en",
        default_story_category="auto",
        default_duration_seconds=30,
        default_scene_count=6,
        max_episode_cost_usd=0,
        require_manual_approval=True,
        web_host=host,
        web_port=8000,
        web_job_workers=1,
    )


def test_fastapi_application_factory_opens(tmp_path: Path):
    application = create_web_app(web_settings(tmp_path))

    with TestClient(application) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "host": "127.0.0.1"}


def test_non_localhost_binding_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="127.0.0.1"):
        create_web_app(web_settings(tmp_path, host="0.0.0.0"))
