from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from animation.models import SceneAnimation
from animation.runway_provider import RunwayVideoProvider


@pytest.fixture
def runway_tmp_path():
    root = Path(".test_tmp")
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def make_scene(tmp_path):
    image = tmp_path / "reference.png"
    image.write_bytes(b"png-data")
    return SceneAnimation(
        image_path=image,
        animation_prompt="Leo and Scout move naturally.",
        duration=5,
        camera_motion="slow push-in",
        output_video=tmp_path / "output" / "scene.mp4",
    )


def test_missing_api_key_fails_without_calling_api(runway_tmp_path):
    scene = make_scene(runway_tmp_path)
    provider = RunwayVideoProvider(api_key="")

    result = provider.generate_scene(scene)

    assert result.status == "failed"
    assert "RUNWAY_API_KEY" in result.error
    assert not scene.output_video.exists()


def test_successful_task_is_polled_and_downloaded(runway_tmp_path):
    scene = make_scene(runway_tmp_path)
    created = SimpleNamespace(id="task-123")
    pending = SimpleNamespace(status="PENDING")
    succeeded = SimpleNamespace(
        status="SUCCEEDED", output=["https://example.test/video.mp4"]
    )
    calls = []

    class Tasks:
        def retrieve(self, task_id):
            calls.append(task_id)
            return pending if len(calls) == 1 else succeeded

    class ImageToVideo:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return created

    image_to_video = ImageToVideo()
    client = SimpleNamespace(image_to_video=image_to_video, tasks=Tasks())

    def downloader(url, output):
        assert url == "https://example.test/video.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"mp4-data")

    provider = RunwayVideoProvider(
        api_key="test-key",
        client=client,
        sleeper=lambda seconds: None,
        downloader=downloader,
    )
    result = provider.generate_scene(scene)

    assert result.status == "generated"
    assert scene.output_video.read_bytes() == b"mp4-data"
    assert image_to_video.kwargs["model"] == "gen4_turbo"
    assert image_to_video.kwargs["ratio"] == "1280:720"
    assert image_to_video.kwargs["duration"] == 5
    assert image_to_video.kwargs["prompt_image"].startswith(
        "data:image/png;base64,"
    )
    assert calls == ["task-123", "task-123"]


def test_scene_duration_is_forwarded_to_runway(runway_tmp_path):
    scene = make_scene(runway_tmp_path)
    scene = SceneAnimation(
        scene.image_path,
        scene.animation_prompt,
        8,
        scene.camera_motion,
        scene.output_video,
    )
    image_to_video = SimpleNamespace(
        create=lambda **kwargs: (
            setattr(image_to_video, "kwargs", kwargs)
            or SimpleNamespace(id="task")
        )
    )
    client = SimpleNamespace(
        image_to_video=image_to_video,
        tasks=SimpleNamespace(
            retrieve=lambda task_id: SimpleNamespace(
                status="SUCCEEDED", output=["https://example.test/video.mp4"]
            )
        ),
    )

    def downloader(url, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video")

    provider = RunwayVideoProvider(
        api_key="test-key", client=client, downloader=downloader
    )
    provider.generate_scene(scene)

    assert image_to_video.kwargs["duration"] == 8


def test_failed_task_returns_actionable_error(runway_tmp_path):
    scene = make_scene(runway_tmp_path)
    failed = SimpleNamespace(
        status="FAILED", failure="content moderation rejected the task"
    )
    client = SimpleNamespace(
        image_to_video=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(id="failed-task")
        ),
        tasks=SimpleNamespace(retrieve=lambda task_id: failed),
    )
    provider = RunwayVideoProvider(
        api_key="test-key",
        client=client,
        sleeper=lambda seconds: None,
    )

    result = provider.generate_scene(scene)

    assert result.status == "failed"
    assert "content moderation" in result.error
    assert not scene.output_video.exists()


def test_polling_timeout_returns_error(runway_tmp_path):
    scene = make_scene(runway_tmp_path)
    client = SimpleNamespace(
        image_to_video=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(id="slow-task")
        ),
        tasks=SimpleNamespace(
            retrieve=lambda task_id: SimpleNamespace(status="PENDING")
        ),
    )
    clock = iter([0.0, 0.0, 2.0])
    provider = RunwayVideoProvider(
        api_key="test-key",
        client=client,
        timeout=1,
        sleeper=lambda seconds: None,
        monotonic=lambda: next(clock),
    )

    result = provider.generate_scene(scene)

    assert result.status == "failed"
    assert "timeout" in result.error.lower()
