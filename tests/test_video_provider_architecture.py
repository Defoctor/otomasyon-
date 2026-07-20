from pathlib import Path
from types import SimpleNamespace

import pytest

from animation.factory import create_video_provider
from animation.higgsfield_service import HiggsfieldVideoProvider
from animation.models import AnimationResult, SceneAnimation
from animation.provider import VideoProvider, VideoProviderConfigurationError


class StubVideoProvider(VideoProvider):
    provider_name = "stub"

    def generate_scene(self, scene):
        return AnimationResult(scene, "generated", ["stub"], scene.output_video)


def test_factory_disables_video_generation_with_none():
    settings = SimpleNamespace(video_provider="none")

    assert create_video_provider(settings) is None


def test_factory_resolves_provider_from_registry():
    settings = SimpleNamespace(video_provider="stub")
    provider = create_video_provider(
        settings, builders={"stub": lambda unused: StubVideoProvider()}
    )

    assert isinstance(provider, VideoProvider)
    assert provider.provider_name == "stub"


def test_generic_provider_generates_all_scenes():
    provider = StubVideoProvider()
    scenes = [
        SceneAnimation(
            image_path=Path(f"scene_{number}.png"),
            animation_prompt="Natural motion.",
            duration=5,
            camera_motion="push-in",
            output_video=Path(f"scene_{number}.mp4"),
        )
        for number in (1, 2)
    ]

    results = provider.generate_all(scenes)

    assert [result.status for result in results] == ["generated", "generated"]


def test_unknown_provider_fails_with_available_provider_names():
    settings = SimpleNamespace(video_provider="unknown")

    with pytest.raises(VideoProviderConfigurationError, match="higgsfield"):
        create_video_provider(settings)


def test_factory_exposes_runway_provider():
    assert "runway" in __import__(
        "animation.factory", fromlist=["PROVIDER_BUILDERS"]
    ).PROVIDER_BUILDERS


def test_higgsfield_implements_generic_contract():
    assert isinstance(HiggsfieldVideoProvider(dry_run=True), VideoProvider)
