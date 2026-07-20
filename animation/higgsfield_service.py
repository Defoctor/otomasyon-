import json
from pathlib import Path
import shlex
import subprocess
from typing import Any, Callable
from urllib.request import urlopen

from .models import AnimationResult, SceneAnimation
from .provider import VideoProvider


class HiggsfieldVideoProvider(VideoProvider):
    """Generate scene clips through the official Higgsfield CLI."""

    provider_name = "higgsfield"

    def __init__(
        self,
        api_key: str = "",
        model: str = "kling3_0",
        output_dir: Path | None = None,
        dry_run: bool = True,
        executable: str = "higgsfield",
        lip_sync: bool = True,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        downloader: Callable[[str, Path], None] | None = None,
    ):
        # api_key/output_dir remain accepted for backward compatibility.
        self.api_key = api_key
        self.model = model
        self.output_dir = output_dir or Path("data/animations")
        self.dry_run = dry_run
        self.executable = executable
        self.lip_sync = lip_sync
        self.runner = runner
        self.downloader = downloader or self._download

    @classmethod
    def from_settings(cls, settings):
        return cls(
            api_key=settings.higgsfield_api_key,
            model=settings.higgsfield_model,
            output_dir=settings.higgsfield_output_dir,
            dry_run=settings.higgsfield_dry_run,
            executable=settings.higgsfield_cli_command,
            lip_sync=settings.higgsfield_lip_sync,
        )

    def build_command(self, scene: SceneAnimation) -> list[str]:
        if not self.model:
            raise ValueError(
                "HIGGSFIELD_MODEL is required (for example: kling3_0)."
            )
        prompt = scene.animation_prompt
        if scene.camera_motion:
            prompt = f"{prompt} Camera motion: {scene.camera_motion}."
        command = [
            self.executable,
            "generate",
            "create",
            self.model,
            "--prompt",
            prompt,
            "--start-image",
            str(scene.image_path.resolve()),
            "--duration",
            str(scene.duration),
        ]
        if self.model in {"kling3_0"}:
            command.extend(["--sound", "off"])
        elif self.model in {"veo3_1", "veo3_1_lite"}:
            command.extend(["--generate_audio", "false"])
        command.extend(["--wait", "--json"])
        return command

    def build_lip_sync_command(
        self, input_video: Path, audio_path: Path
    ) -> list[str]:
        return [
            self.executable,
            "generate",
            "create",
            "sync_so",
            "--input_video",
            str(input_video.resolve()),
            "--input_audio",
            str(audio_path.resolve()),
            "--sync_mode",
            "cut_off",
            "--wait",
            "--json",
        ]

    def generate_scene(self, scene: SceneAnimation) -> AnimationResult:
        command = self.build_command(scene)
        if self.dry_run:
            print(f"[HIGGSFIELD DRY-RUN] {shlex.join(command)}")
            if self.lip_sync and scene.audio_path:
                print(
                    "[HIGGSFIELD DRY-RUN] "
                    + shlex.join(
                        self.build_lip_sync_command(
                            scene.output_video.with_suffix(".base.mp4"),
                            scene.audio_path,
                        )
                    )
                )
            return AnimationResult(scene, "dry_run", command)

        try:
            scene.output_video.parent.mkdir(parents=True, exist_ok=True)
            base_output = (
                scene.output_video.with_suffix(".base.mp4")
                if self.lip_sync and scene.audio_path
                else scene.output_video
            )
            response = self._run_json(command)
            self.downloader(self._find_result_url(response), base_output)

            if self.lip_sync and scene.audio_path:
                lip_command = self.build_lip_sync_command(
                    base_output, scene.audio_path
                )
                response = self._run_json(lip_command)
                self.downloader(
                    self._find_result_url(response), scene.output_video
                )
                base_output.unlink(missing_ok=True)

            if (
                not scene.output_video.exists()
                or scene.output_video.stat().st_size == 0
            ):
                raise RuntimeError("Higgsfield produced an empty video file.")
            return AnimationResult(
                scene, "generated", command, scene.output_video
            )
        except Exception as exc:
            return AnimationResult(
                scene, "failed", command, error=f"{type(exc).__name__}: {exc}"
            )

    # Backward-compatible names for existing callers.
    def submit_scene(self, scene: SceneAnimation) -> AnimationResult:
        return self.generate_scene(scene)

    def submit_all(
        self, scenes: list[SceneAnimation]
    ) -> list[AnimationResult]:
        return self.generate_all(scenes)

    def _run_json(self, command: list[str]) -> Any:
        completed = self.runner(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Higgsfield CLI did not return JSON: {completed.stdout[-500:]}"
            ) from exc

    @classmethod
    def _find_result_url(cls, value: Any) -> str:
        if isinstance(value, dict):
            for key in ("result_url", "url", "output_url"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.startswith("http"):
                    return candidate
            for nested in value.values():
                try:
                    return cls._find_result_url(nested)
                except RuntimeError:
                    pass
        elif isinstance(value, list):
            for nested in value:
                try:
                    return cls._find_result_url(nested)
                except RuntimeError:
                    pass
        elif isinstance(value, str) and value.startswith("http"):
            return value
        raise RuntimeError("Higgsfield response contains no result URL.")

    @staticmethod
    def _download(url: str, output_path: Path) -> None:
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with urlopen(url, timeout=120) as response:
            temporary.write_bytes(response.read())
        temporary.replace(output_path)


# Existing imports keep working while new code uses the generic provider name.
HiggsfieldCliService = HiggsfieldVideoProvider
