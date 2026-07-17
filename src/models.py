from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Scene:
    number: int
    narration: str
    visual_prompt: str
    duration_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentPackage:
    topic: str
    title: str
    description: str
    tags: list[str]
    script: str
    scenes: list[Scene]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

