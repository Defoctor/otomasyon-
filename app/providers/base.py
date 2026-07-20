from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.story import MainCharacter, Scene, Story, StoryCategory


class StoryProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate(
        self,
        episode_id: str,
        category: StoryCategory,
        duration_seconds: int,
        seed: int | None = None,
    ) -> Story:
        """Generate and validate one complete story."""
        raise NotImplementedError


class ImageProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_scene(
        self,
        scene: Scene,
        character: MainCharacter,
        story_category: StoryCategory,
        output_path: Path,
    ) -> Path:
        raise NotImplementedError


class VideoProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_scene(
        self,
        image_path: Path,
        output_path: Path,
        duration_seconds: int,
        scene_number: int,
    ) -> Path:
        raise NotImplementedError


class TTSProvider(ABC):
    provider_name: str

    @abstractmethod
    def synthesize(
        self, text: str, output_path: Path, duration_seconds: int
    ) -> Path:
        raise NotImplementedError


class MusicProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate(
        self, mood: str, output_path: Path, duration_seconds: int
    ) -> Path:
        raise NotImplementedError


class SoundEffectProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate(
        self,
        scenes: list[Scene],
        output_path: Path,
        duration_seconds: int,
    ) -> Path | None:
        raise NotImplementedError
