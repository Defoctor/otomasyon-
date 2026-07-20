from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.animation import (
    HiggsfieldAnimationService,
    HiggsfieldConfigurationError,
    SceneAnimation,
    submit_to_higgsfield,
)


def test_higgsfield_service_builds_submission_without_real_network():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        tmp_path = Path(temp_dir)
        calls = []

        def fake_transport(endpoint, api_key, payload):
            calls.append((endpoint, api_key, payload))
            return {"id": "animation-123", "status": "queued"}

        image = tmp_path / "scene_01.png"
        scene = SceneAnimation(
            image_path=image,
            animation_prompt="Leo and Scout discover a glowing map.",
            duration=8,
            camera_motion="slow push-in",
        )
        service = HiggsfieldAnimationService(
            api_key="test-key",
            endpoint="https://example.invalid/animations",
            transport=fake_transport,
        )

        submission = submit_to_higgsfield(scene, service)

        assert submission.submission_id == "animation-123"
        assert submission.status == "queued"
        assert calls[0][2] == {
            "image_path": str(image.resolve()),
            "animation_prompt": "Leo and Scout discover a glowing map.",
            "duration": 8,
            "camera_motion": "slow push-in",
        }


def test_higgsfield_service_does_not_send_without_configuration(monkeypatch):
    monkeypatch.delenv("HIGGSFIELD_API_KEY", raising=False)
    monkeypatch.delenv("HIGGSFIELD_API_URL", raising=False)
    scene = SceneAnimation(Path("scene.png"), "A gentle breeze.", 5, "static")

    with pytest.raises(HiggsfieldConfigurationError):
        submit_to_higgsfield(scene)
