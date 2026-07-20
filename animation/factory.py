from collections.abc import Callable
from typing import Any

from .higgsfield_service import HiggsfieldVideoProvider
from .runway_provider import RunwayVideoProvider
from .provider import VideoProvider, VideoProviderConfigurationError


ProviderBuilder = Callable[[Any], VideoProvider]


def _higgsfield_builder(settings: Any) -> VideoProvider:
    return HiggsfieldVideoProvider.from_settings(settings)


def _runway_builder(settings: Any) -> VideoProvider:
    return RunwayVideoProvider.from_settings(settings)


PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "higgsfield": _higgsfield_builder,
    "runway": _runway_builder,
}


def create_video_provider(
    settings: Any,
    builders: dict[str, ProviderBuilder] | None = None,
) -> VideoProvider | None:
    """Resolve the selected provider without coupling the pipeline to it."""
    name = settings.video_provider.strip().lower()
    if name in {"", "none", "disabled"}:
        return None

    available = builders or PROVIDER_BUILDERS
    builder = available.get(name)
    if builder is None:
        supported = ", ".join(sorted(available)) or "(none)"
        raise VideoProviderConfigurationError(
            f"Unsupported VIDEO_PROVIDER: {name!r}. Available: {supported}."
        )
    return builder(settings)
