from pathlib import Path
import sqlite3

from app.database import Database, EpisodeRepository
from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory


EXPECTED_TABLES = {
    "episodes",
    "characters",
    "scenes",
    "generation_jobs",
    "assets",
    "quality_reports",
    "youtube_uploads",
    "performance_metrics",
    "story_experiments",
    "web_generation_jobs",
}


def test_database_initializes_all_stage_one_tables(tmp_path: Path):
    database = Database(tmp_path / "kids_shorts.db")
    database.initialize()

    assert EpisodeRepository(database).table_names() == EXPECTED_TABLES


def test_repository_saves_story_and_six_scenes(tmp_path: Path):
    database = Database(tmp_path / "kids_shorts.db")
    database.initialize()
    repository = EpisodeRepository(database)
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=5
    )

    saved_id = repository.save_story(
        story,
        str(tmp_path / "episode_0001" / "story.json"),
        provider_name="mock",
        idempotency_key="stable-test-key",
    )

    assert saved_id == "episode_0001"
    assert repository.get_episode("episode_0001")["approval_status"] == "pending"
    with database.connect() as connection:
        scene_count = connection.execute(
            "SELECT COUNT(*) AS count FROM scenes WHERE episode_id = ?",
            ("episode_0001",),
        ).fetchone()["count"]
        job = connection.execute(
            "SELECT status FROM generation_jobs WHERE episode_id = ?",
            ("episode_0001",),
        ).fetchone()
    assert scene_count == 6
    assert job["status"] == "completed"


def test_foreign_keys_are_enforced(tmp_path: Path):
    database = Database(tmp_path / "kids_shorts.db")
    database.initialize()

    with database.connect() as connection:
        try:
            connection.execute(
                """
                INSERT INTO scenes (
                    episode_id, scene_number, duration_seconds, narration,
                    visual_prompt, motion_prompt, emotion
                ) VALUES ('missing', 1, 5, 'n', 'v', 'm', 'happy')
                """
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("SQLite foreign key constraint was not enforced.")
