import json
from pathlib import Path

from app.core.config import Settings
from app.pipeline import DemoVideoPipeline, StoryPipeline
from app.rendering.ffmpeg import probe_media, resolve_media_tool


def stage_two_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        log_level="INFO",
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
        video_width=324,
        video_height=576,
        video_fps=30,
        audio_sample_rate=48_000,
    )


def test_end_to_end_stage_two_pipeline_low_resolution(tmp_path: Path):
    settings = stage_two_settings(tmp_path)
    story_result = StoryPipeline(settings).run(seed=22)

    result = DemoVideoPipeline(settings).run(story_result.episode_id)

    assert len(list(result.images_directory.glob("scene_*.png"))) == 6
    assert len(list(result.clips_directory.glob("scene_*.mp4"))) == 6
    assert result.final_video_path.is_file()
    report = json.loads(
        result.quality_report_path.read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"
    probe = probe_media(result.final_video_path, resolve_media_tool("ffprobe"))
    assert abs(float(probe["format"]["duration"]) - 30) < 0.35
