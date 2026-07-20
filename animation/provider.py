from abc import ABC, abstractmethod

from .models import AnimationResult, SceneAnimation


class VideoProvider(ABC):
    """Provider-independent contract for scene video generation."""

    provider_name: str

    @abstractmethod
    def generate_scene(self, scene: SceneAnimation) -> AnimationResult:
        raise NotImplementedError

    def generate_all(
        self, scenes: list[SceneAnimation]
    ) -> list[AnimationResult]:
        return [self.generate_scene(scene) for scene in scenes]


class VideoProviderConfigurationError(RuntimeError):
    pass
