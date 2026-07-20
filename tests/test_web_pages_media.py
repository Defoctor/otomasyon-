from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Database, EpisodeRepository
from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory
from app.web import create_web_app
from tests.test_web_app import web_settings


def seed_episode(settings, episode_id: str = "episode_0001"):
    database = Database(settings.database_path)
    database.initialize()
    story = MockStoryProvider().generate(
        episode_id, StoryCategory.ANIMAL_RESCUE, 30, seed=7
    )
    directory = settings.output_dir / episode_id
    directory.mkdir(parents=True)
    (directory / "story.json").write_text(
        story.model_dump_json(indent=2), encoding="utf-8"
    )
    (directory / "character_bible.json").write_text(
        story.character_bible.model_dump_json(indent=2), encoding="utf-8"
    )
    (directory / "metadata.json").write_text("{}", encoding="utf-8")
    EpisodeRepository(database).save_story(
        story,
        str(directory / "story.json"),
        "mock",
        f"seed-{episode_id}",
    )
    return directory


def test_dashboard_episode_list_and_detail(tmp_path: Path):
    settings = web_settings(tmp_path)
    seed_episode(settings)
    application = create_web_app(settings)

    with TestClient(application) as client:
        dashboard = client.get("/")
        listing = client.get("/episodes")
        detail = client.get("/episodes/episode_0001")
        api = client.get("/api/episodes/episode_0001")

    assert dashboard.status_code == 200
    assert "Kids Shorts" in dashboard.text
    assert listing.status_code == 200
    assert "episode_0001" in listing.text
    assert detail.status_code == 200
    assert "Six scenes" in detail.text
    assert api.status_code == 200
    assert api.json()["episode"]["episode_id"] == "episode_0001"


def test_media_endpoint_supports_range_and_blocks_traversal(tmp_path: Path):
    settings = web_settings(tmp_path)
    directory = seed_episode(settings)
    video = directory / "final_short.mp4"
    video.write_bytes(bytes(range(256)) * 8)
    application = create_web_app(settings)

    with TestClient(application) as client:
        full = client.get("/media/episode_0001/final_short.mp4")
        partial = client.get(
            "/media/episode_0001/final_short.mp4",
            headers={"Range": "bytes=0-99"},
        )
        traversal = client.get(
            "/media/episode_0001/%2E%2E%2Fstory.json"
        )

    assert full.status_code == 200
    assert partial.status_code == 206
    assert partial.headers["content-range"].startswith("bytes 0-99/")
    assert len(partial.content) == 100
    assert traversal.status_code in {403, 404}
