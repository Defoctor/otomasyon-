from pathlib import Path

from app.providers.base import VideoProvider
from app.rendering.ffmpeg import run_checked


class LocalMotionVideoProvider(VideoProvider):
    provider_name = "local_motion"

    def __init__(
        self,
        ffmpeg_path: Path,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        preset: str = "veryfast",
    ):
        self.ffmpeg_path = ffmpeg_path
        self.width = width
        self.height = height
        self.fps = fps
        self.preset = preset

    def generate_scene(
        self,
        image_path: Path,
        output_path: Path,
        duration_seconds: int,
        scene_number: int,
    ) -> Path:
        if not image_path.is_file():
            raise FileNotFoundError(f"Scene image not found: {image_path}")
        if duration_seconds <= 0:
            raise ValueError("Scene duration must be positive.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        frames = int(duration_seconds * self.fps)
        zoom, x, y = _motion(scene_number, frames)
        filter_graph = (
            f"scale={self.width}:{self.height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},"
            f"zoompan=z='{zoom}':x='{x}':y='{y}':"
            f"d=1:s={self.width}x{self.height}:fps={self.fps},"
            "format=yuv420p"
        )
        try:
            run_checked(
                [
                    str(self.ffmpeg_path),
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(image_path),
                    "-vf",
                    filter_graph,
                    "-t",
                    str(duration_seconds),
                    "-r",
                    str(self.fps),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    self.preset,
                    "-crf",
                    "22",
                    "-movflags",
                    "+faststart",
                    "-f",
                    "mp4",
                    str(temporary),
                ],
                f"Local motion render for scene {scene_number}",
            )
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError(
                    f"Local motion scene {scene_number} produced no video."
                )
            temporary.replace(output_path)
            return output_path
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def _motion(scene_number: int, frames: int) -> tuple[str, str, str]:
    progress = f"on/{max(1, frames - 1)}"
    motions = [
        (
            f"min(1.0+0.08*{progress},1.08)",
            "iw/2-(iw/zoom/2)",
            "ih/2-(ih/zoom/2)",
        ),
        ("1.08", f"(iw-iw/zoom)*{progress}", "ih/2-(ih/zoom/2)"),
        (
            f"max(1.08-0.08*{progress},1.0)",
            "iw/2-(iw/zoom/2)",
            "ih/2-(ih/zoom/2)",
        ),
        ("1.08", f"(iw-iw/zoom)*(1-{progress})", "ih/2-(ih/zoom/2)"),
        ("1.08", "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*{progress}"),
        (
            f"min(1.02+0.04*{progress},1.06)",
            "iw/2-(iw/zoom/2)",
            "ih/2-(ih/zoom/2)",
        ),
    ]
    return motions[(scene_number - 1) % len(motions)]
