import pytest

from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory


def test_mock_provider_is_deterministic_for_same_seed():
    provider = MockStoryProvider()

    first = provider.generate(
        "episode_0001", StoryCategory.UNEXPECTED_FRIENDSHIP, 30, seed=42
    )
    second = provider.generate(
        "episode_0001", StoryCategory.UNEXPECTED_FRIENDSHIP, 30, seed=42
    )

    assert first == second
    assert first.story_category == StoryCategory.UNEXPECTED_FRIENDSHIP


@pytest.mark.parametrize("duration", [25, 30, 35])
def test_mock_provider_supports_target_duration_range(duration):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, duration, seed=1
    )

    assert sum(scene.duration_seconds for scene in story.scenes) == duration
    assert all(4 <= scene.duration_seconds <= 6 for scene in story.scenes)


def test_mock_provider_rejects_invalid_duration():
    with pytest.raises(ValueError, match="between 25 and 35"):
        MockStoryProvider().generate(
            "episode_0001", StoryCategory.ANIMAL_RESCUE, 36
        )


def test_different_seeds_change_title_plot_scenes_and_ending():
    provider = MockStoryProvider()
    first = provider.generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=101
    )
    second = provider.generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=202
    )

    assert first.title != second.title
    assert first.content_summary != second.content_summary
    assert [scene.narration for scene in first.scenes] != [
        scene.narration for scene in second.scenes
    ]
    assert first.scenes[-1].narration != second.scenes[-1].narration


def test_different_categories_change_story_structure_with_same_seed():
    provider = MockStoryProvider()
    rescue = provider.generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=77
    )
    mystery = provider.generate(
        "episode_0001", StoryCategory.MYSTERY_OBJECT, 30, seed=77
    )

    assert rescue.title != mystery.title
    assert rescue.hook_type != mystery.hook_type
    assert rescue.scenes[2].narration != mystery.scenes[2].narration
    assert rescue.ending_type != mystery.ending_type
