from pathlib import Path

from app.database import Database, EpisodeRepository
from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory


def test_stage_two_asset_and_completion_records(tmp_path: Path):
    database = Database(tmp_path / "kids_shorts.db")
    database.initialize()
    repository = EpisodeRepository(database)
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=1
    )
    repository.save_story(
        story,
        str(tmp_path / "story.json"),
        "mock",
        "stage2-db-test",
    )

    repository.start_stage_two("episode_0001")
    repository.record_asset(
        "episode_0001",
        "image",
        "placeholder",
        str(tmp_path / "scene_01.png"),
        scene_number=1,
    )
    repository.complete_stage_two(
        "episode_0001",
        str(tmp_path / "final_short.mp4"),
        str(tmp_path / "quality_report.json"),
        {"image": "placeholder", "render": "ffmpeg"},
    )

    episode = repository.get_episode("episode_0001")
    assert episode["generation_status"] == "completed"
    assert episode["approval_status"] == "pending"
    assert episode["upload_status"] == "not_ready"
    with database.connect() as connection:
        assets = connection.execute(
            "SELECT COUNT(1) AS count FROM assets"
        ).fetchone()["count"]
        quality = connection.execute(
            "SELECT passed FROM quality_reports WHERE episode_id = ?",
            ("episode_0001",),
        ).fetchone()
        job = connection.execute(
            "SELECT status FROM generation_jobs WHERE episode_id = ?",
            ("episode_0001",),
        ).fetchone()
    assert assets == 1
    assert quality["passed"] == 1
    assert job["status"] == "completed"
