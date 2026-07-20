from pathlib import Path

from app.providers.story import MockStoryProvider
from app.rendering.subtitles import create_subtitles
from app.schemas.story import StoryCategory


def test_srt_uses_scene_timing_and_ends_at_story_duration(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=4
    )
    srt = tmp_path / "subtitles.srt"
    ass = tmp_path / "subtitles.ass"

    create_subtitles(story.scenes, srt, ass)
    content = srt.read_text(encoding="utf-8")

    assert "00:00:00,000 --> 00:00:05,000" in content
    assert "00:00:25,000 --> 00:00:30,000" in content
    assert content.count(" --> ") == 6


def test_ass_has_mobile_safe_style_and_two_line_events(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=4
    )
    srt = tmp_path / "subtitles.srt"
    ass = tmp_path / "subtitles.ass"

    create_subtitles(story.scenes, srt, ass)
    content = ass.read_text(encoding="utf-8")
    events = [line for line in content.splitlines() if line.startswith("Dialogue:")]

    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Style: Default,Arial,72" in content
    assert len(events) == 6
    assert all(event.count(r"\N") <= 1 for event in events)
    assert all("…" not in event for event in events)
    assert ",1,6,2,2,108,108,250,1" in content


def test_subtitle_line_break_preserves_every_narration_word(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=4
    )
    srt = tmp_path / "subtitles.srt"
    ass = tmp_path / "subtitles.ass"

    create_subtitles(story.scenes, srt, ass)
    content = srt.read_text(encoding="utf-8")

    for scene in story.scenes:
        assert scene.narration in content.replace("\n", " ")
