import base64
import mimetypes
from pathlib import Path
import time
from typing import Any, Callable
from urllib.request import urlopen

from .models import AnimationResult, SceneAnimation
from .provider import VideoProvider


class RunwayVideoProvider(VideoProvider):
    """Runway Gen-4 Turbo image-to-video adapter."""

    provider_name = "runway"

    def __init__(
        self,
        api_key: str,
        model: str = "gen4_turbo",
        ratio: str = "1280:720",
        duration: int = 5,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
        max_retries: int = 3,
        client: Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        downloader: Callable[[str, Path], None] | None = None,
    ):
        if model != "gen4_turbo":
            raise ValueError("Initial Runway integration only supports gen4_turbo.")
        if ratio != "1280:720":
            raise ValueError("Initial Runway integration only supports 1280:720.")
        if not 2 <= duration <= 10:
            raise ValueError("RUNWAY_DURATION must be between 2 and 10 seconds.")
        if poll_interval < 5:
            raise ValueError("RUNWAY_POLL_INTERVAL must be at least 5 seconds.")

        self.api_key = api_key
        self.model = model
        self.ratio = ratio
        self.duration = duration
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = client
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.downloader = downloader or self._download

    @classmethod
    def from_settings(cls, settings):
        return cls(
            api_key=settings.runway_api_key,
            model=settings.runway_model,
            ratio=settings.runway_ratio,
            duration=settings.runway_duration,
            poll_interval=settings.runway_poll_interval,
            timeout=settings.runway_timeout,
            max_retries=settings.runway_max_retries,
        )

    def generate_scene(self, scene: SceneAnimation) -> AnimationResult:
        duration = min(10, max(2, scene.duration))
        operation = [
            "runway",
            "image_to_video",
            self.model,
            self.ratio,
            f"{duration}s",
        ]
        if not self.api_key:
            return AnimationResult(
                scene,
                "failed",
                operation,
                error="RUNWAY_API_KEY is not configured; no API call was made.",
            )
        if not scene.image_path.is_file():
            return AnimationResult(
                scene,
                "failed",
                operation,
                error=f"Reference image not found: {scene.image_path}",
            )

        try:
            prompt = scene.animation_prompt
            if scene.camera_motion:
                prompt = f"{prompt} Camera motion: {scene.camera_motion}."
            task = self._get_client().image_to_video.create(
                model=self.model,
                prompt_image=self._image_data_uri(scene.image_path),
                prompt_text=prompt,
                ratio=self.ratio,
                duration=duration,
            )
            completed = self._poll_task(str(task.id))
            output = getattr(completed, "output", None) or []
            if not output or not isinstance(output[0], str):
                raise RuntimeError("Runway task succeeded without a video URL.")

            scene.output_video.parent.mkdir(parents=True, exist_ok=True)
            self._retry(
                lambda: self.downloader(output[0], scene.output_video),
                "video download",
            )
            if (
                not scene.output_video.exists()
                or scene.output_video.stat().st_size == 0
            ):
                raise RuntimeError("Runway produced an empty MP4 file.")
            return AnimationResult(
                scene, "generated", operation, scene.output_video
            )
        except Exception as exc:
            return AnimationResult(
                scene,
                "failed",
                operation,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _get_client(self):
        if self._client is None:
            from runwayml import RunwayML

            self._client = RunwayML(api_key=self.api_key)
        return self._client

    def _poll_task(self, task_id: str):
        deadline = self.monotonic() + self.timeout
        while self.monotonic() < deadline:
            task = self._retry(
                lambda: self._get_client().tasks.retrieve(task_id),
                "task polling",
            )
            status = str(getattr(task, "status", "")).upper()
            if status == "SUCCEEDED":
                return task
            if status in {"FAILED", "CANCELED"}:
                details = getattr(task, "failure", None) or getattr(
                    task, "failure_code", None
                )
                raise RuntimeError(
                    f"Runway task ended with {status}: {details or 'no details'}"
                )
            self.sleeper(self.poll_interval)
        raise TimeoutError(
            f"Runway task {task_id} exceeded {self.timeout:.0f}s timeout."
        )

    def _retry(self, action: Callable[[], Any], label: str):
        for attempt in range(self.max_retries + 1):
            try:
                return action()
            except Exception as exc:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"Runway {label} failed after "
                        f"{self.max_retries + 1} attempts: {exc}"
                    ) from exc
                self.sleeper(min(2 ** attempt, 30))

    @staticmethod
    def _image_data_uri(path: Path) -> str:
        media_type = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{media_type};base64,{encoded}"

    @staticmethod
    def _download(url: str, output_path: Path) -> None:
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with urlopen(url, timeout=120) as response:
            temporary.write_bytes(response.read())
        temporary.replace(output_path)
