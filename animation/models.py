from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class SceneAnimation:
    image_path: Path
    animation_prompt: str
    duration: int
    camera_motion: str
    output_video: Path
    audio_path: Path | None = None


@dataclass(frozen=True)
class AnimationResult:
    scene: SceneAnimation
    status: Literal["generated", "dry_run", "failed"]
    command: list[str]
    output_video: Path | None = None
    error: str | None = None
