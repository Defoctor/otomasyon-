from pathlib import Path

from src.models import ContentPackage

from .models import SceneAnimation


def build_animation_plan(
    project_dir: Path,
    content: ContentPackage,
    camera_motion: str = "gentle cinematic push-in",
) -> list[SceneAnimation]:
    return [
        SceneAnimation(
            image_path=project_dir / "images" / f"scene_{scene.number:02d}.png",
            animation_prompt=scene.visual_prompt,
            duration=scene.duration_seconds,
            camera_motion=camera_motion,
        )
        for scene in content.scenes
    ]
