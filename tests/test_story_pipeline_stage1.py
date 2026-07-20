import json
from pathlib import Path

from app.core.config import Settings
from app.pipeline import StoryPipeline
from app.schemas.story import Story


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        log_level="DEBUG",
        demo_mode=True,
        story_provider="mock",
        output_dir=tmp_path / "output",
        database_path=tmp_path / "data" / "kids_shorts.db",
        default_language="en",
        default_story_category="auto",
        default_duration_seconds=30,
        default_scene_count=6,
        max_episode_cost_usd=0,
        require_manual_approval=True,
    )


def test_stage_one_pipeline_writes_valid_episode_package(tmp_path: Path):
    settings = make_settings(tmp_path)

    result = StoryPipeline(settings).run(seed=11)

    assert result.episode_id == "episode_0001"
    assert result.story_path.is_file()
    assert result.character_bible_path.is_file()
    assert result.metadata_path.is_file()
    story = Story.model_validate_json(
        result.story_path.read_text(encoding="utf-8")
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert len(story.scenes) == 6
    assert metadata["demo_mode"] is True
    assert metadata["requires_manual_approval"] is True
    assert metadata["generation_cost_estimate_usd"] == 0


def test_pipeline_never_overwrites_existing_episode_directory(tmp_path: Path):
    settings = make_settings(tmp_path)
    old = settings.output_dir / "episode_0007"
    old.mkdir(parents=True)
    (old / "keep.txt").write_text("user data", encoding="utf-8")

    result = StoryPipeline(settings).run(seed=12)

    assert result.episode_id == "episode_0008"
    assert (old / "keep.txt").read_text(encoding="utf-8") == "user data"


def test_empty_seed_generates_and_persists_a_new_safe_seed(tmp_path: Path):
    settings = make_settings(tmp_path)

    first = StoryPipeline(settings).run()
    second = StoryPipeline(settings).run()
    first_metadata = json.loads(first.metadata_path.read_text(encoding="utf-8"))
    second_metadata = json.loads(second.metadata_path.read_text(encoding="utf-8"))

    assert first.generation_seed >= 0
    assert second.generation_seed >= 0
    assert first.generation_seed != second.generation_seed
    assert first_metadata["generation_seed"] == first.generation_seed
    assert second_metadata["generation_seed"] == second.generation_seed
    assert first.story_path.read_text(encoding="utf-8") != second.story_path.read_text(encoding="utf-8")
