from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from animation.higgsfield_service import HiggsfieldCliService
from animation.models import SceneAnimation


def test_higgsfield_cli_dry_run_only_builds_command(capsys):
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        scene = SceneAnimation(
            image_path=root / "scene_01.png",
            animation_prompt="Subtle movement in the forest.",
            duration=6,
            camera_motion="slow push-in",
            output_video=root / "scene_01.mp4",
        )
        service = HiggsfieldCliService(
            model="test-model",
            output_dir=root,
            dry_run=True,
        )

        result = service.submit_scene(scene)
        command = result.command
        output = capsys.readouterr().out

        assert command[0:4] == [
            "higgsfield",
            "generate",
            "create",
            "test-model",
        ]
        assert "--start-image" in command
        assert "--wait" in command
        assert "--json" in command
        prompt = command[command.index("--prompt") + 1]
        assert "Camera motion: slow push-in." in prompt
        assert "[HIGGSFIELD DRY-RUN]" in output
        assert result.status == "dry_run"
        assert not scene.output_video.exists()


def test_legacy_api_key_is_not_forwarded_to_cli(monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "must-not-be-forwarded")
    service = HiggsfieldCliService(api_key="legacy-value", dry_run=True)
    scene = SceneAnimation(
        image_path=Path("scene.png"),
        animation_prompt="A gentle breeze.",
        duration=5,
        camera_motion="static",
        output_video=Path("scene.mp4"),
    )

    command = service.build_command(scene)

    assert "must-not-be-forwarded" not in command
    assert "legacy-value" not in command


def test_higgsfield_downloads_generated_clip():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        scene = SceneAnimation(
            image_path=root / "scene.png",
            animation_prompt="Leo waves.",
            duration=5,
            camera_motion="push-in",
            output_video=root / "animated_clips" / "scene_01.mp4",
        )

        def runner(command, **kwargs):
            return subprocess.CompletedProcess(
                command, 0, stdout='{"result_url":"https://example/video.mp4"}'
            )

        def downloader(url, output):
            assert url == "https://example/video.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"fake-mp4")

        result = HiggsfieldCliService(
            dry_run=False,
            runner=runner,
            downloader=downloader,
        ).submit_scene(scene)

        assert result.status == "generated"
        assert scene.output_video.read_bytes() == b"fake-mp4"


def test_veo_lite_uses_its_documented_audio_flag():
    service = HiggsfieldCliService(model="veo3_1_lite", dry_run=True)
    scene = SceneAnimation(
        image_path=Path("scene.png"),
        animation_prompt="Leo and Scout move naturally.",
        duration=6,
        camera_motion="push-in",
        output_video=Path("scene.mp4"),
    )

    command = service.build_command(scene)

    assert "--generate_audio" in command
    assert command[command.index("--generate_audio") + 1] == "false"
    assert "--sound" not in command
