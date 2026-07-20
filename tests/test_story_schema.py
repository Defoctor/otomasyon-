import pytest
from pydantic import ValidationError

from app.providers.story import MockStoryProvider
from app.schemas.story import Story, StoryCategory


def make_story() -> Story:
    return MockStoryProvider().generate(
        "episode_0001",
        StoryCategory.ANIMAL_RESCUE,
        duration_seconds=30,
        seed=7,
    )


def test_story_schema_accepts_valid_six_scene_story():
    story = make_story()

    assert len(story.scenes) == 6
    assert [scene.scene_number for scene in story.scenes] == list(range(1, 7))
    assert sum(scene.duration_seconds for scene in story.scenes) == 30
    assert story.language == "en"


def test_character_lock_is_present_unchanged_in_every_prompt():
    story = make_story()
    signature = story.character_bible.main_character.prompt_signature()

    assert all(signature in scene.visual_prompt for scene in story.scenes)


def test_story_schema_rejects_missing_character_lock():
    data = make_story().model_dump(mode="json")
    data["scenes"][2]["visual_prompt"] = (
        "A sufficiently detailed but inconsistent visual prompt without lock."
    )

    with pytest.raises(ValidationError, match="Character lock is missing"):
        Story.model_validate(data)


def test_story_schema_rejects_duration_outside_shorts_target():
    data = make_story().model_dump(mode="json")
    data["duration_target_seconds"] = 35

    with pytest.raises(ValidationError, match="must equal total"):
        Story.model_validate(data)
