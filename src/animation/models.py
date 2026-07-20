from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SceneAnimation:
    image_path: Path
    animation_prompt: str
    duration: int
    camera_motion: str

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["image_path"] = str(self.image_path.resolve())
        return payload


@dataclass(frozen=True)
class AnimationSubmission:
    submission_id: str
    status: str
    raw_response: dict[str, Any]
