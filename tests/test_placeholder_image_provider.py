from pathlib import Path

from PIL import Image

from app.providers.image import PlaceholderImageProvider
from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory


def test_placeholder_image_has_vertical_resolution(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=2
    )
    output = tmp_path / "scene_01.png"

    PlaceholderImageProvider().generate_scene(
        story.scenes[0],
        story.character_bible.main_character,
        story.story_category,
        output,
    )

    assert output.is_file()
    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        assert image.mode == "RGB"


def test_placeholder_provider_creates_six_distinct_text_free_images(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.LOST_BABY_ANIMAL, 30, seed=3
    )
    provider = PlaceholderImageProvider()

    outputs = [
        provider.generate_scene(
            scene,
            story.character_bible.main_character,
            story.story_category,
            tmp_path / f"scene_{scene.scene_number:02d}.png",
        )
        for scene in story.scenes
    ]

    assert len(outputs) == 6
    assert all(path.stat().st_size > 0 for path in outputs)
    assert provider.contains_text is False
    image_bytes = [path.read_bytes() for path in outputs]
    assert len(set(image_bytes)) == 6


def test_first_scene_has_high_contrast_hook_composition(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=3
    )
    output = tmp_path / "scene_01.png"
    PlaceholderImageProvider().generate_scene(
        story.scenes[0],
        story.character_bible.main_character,
        story.story_category,
        output,
    )

    with Image.open(output) as image:
        colors = image.resize((90, 160)).getcolors(maxcolors=90 * 160)
    assert colors is not None
    assert len(colors) >= 12
