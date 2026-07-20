import json
from pathlib import Path

from app.core.config import Settings
from app.pipeline import DemoVideoPipeline, StoryPipeline
from app.rendering.ffmpeg import probe_media, resolve_media_tool


def test_real_1080x1920_stage_two_integration(tmp_path: Path):
    settings = Settings(
        app_env="integration",
        log_level="INFO",
        demo_mode=True,
        story_provider="mock",
        output_dir=tmp_path / "output",
        database_path=tmp_path / "data" / "kids_shorts.db",
        default_language="en",
        default_story_category="animal_rescue",
        default_duration_seconds=25,
        default_scene_count=6,
        max_episode_cost_usd=0,
        require_manual_approval=True,
        video_width=1080,
        video_height=1920,
        video_fps=30,
        audio_sample_rate=48_000,
    )
    story_result = StoryPipeline(settings).run(
        duration_seconds=25, seed=1080
    )

    result = DemoVideoPipeline(settings).run(story_result.episode_id)

    probe = probe_media(result.final_video_path, resolve_media_tool("ffprobe"))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    report = json.loads(
        result.quality_report_path.read_text(encoding="utf-8")
    )
    assert (video["width"], video["height"]) == (1080, 1920)
    assert video["codec_name"] == "h264"
    assert audio["codec_name"] == "aac"
    assert abs(float(probe["format"]["duration"]) - 25) < 0.35
    assert report["status"] == "passed"
