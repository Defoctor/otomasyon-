from pathlib import Path

from PIL import Image

from app.audio import mix_audio
from app.providers.music import GeneratedDemoMusicProvider
from app.providers.sound_effects import GeneratedDemoSoundEffectProvider
from app.providers.story import MockStoryProvider
from app.providers.tts import MockNarrationProvider
from app.providers.video import LocalMotionVideoProvider
from app.rendering.ffmpeg import probe_media, resolve_media_tool
from app.rendering.final_renderer import render_final_video
from app.rendering.subtitles import create_subtitles
from app.schemas.story import StoryCategory


def test_final_renderer_creates_h264_aac_video_with_burned_subtitles(
    tmp_path: Path,
):
    ffmpeg = resolve_media_tool("ffmpeg")
    ffprobe = resolve_media_tool("ffprobe")
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=1
    )
    image = tmp_path / "image.png"
    Image.new("RGB", (320, 568), "#547A95").save(image)
    provider = LocalMotionVideoProvider(
        ffmpeg, width=320, height=568, preset="ultrafast"
    )
    clips = []
    for number in range(1, 7):
        clip = tmp_path / f"clip_{number}.mp4"
        provider.generate_scene(image, clip, 1, number)
        clips.append(clip)
    narration = tmp_path / "narration.wav"
    music = tmp_path / "music.wav"
    effects = tmp_path / "effects.wav"
    final_mix = tmp_path / "final_mix.wav"
    MockNarrationProvider().synthesize("Short test narration.", narration, 6)
    GeneratedDemoMusicProvider().generate("uplifting", music, 6)
    GeneratedDemoSoundEffectProvider().generate(story.scenes, effects, 6)
    mix_audio(ffmpeg, narration, music, effects, final_mix, 6)
    srt = tmp_path / "subtitles.srt"
    ass = tmp_path / "subtitles.ass"
    create_subtitles(story.scenes, srt, ass, width=320, height=568)
    output = tmp_path / "final.mp4"

    render_final_video(
        ffmpeg,
        clips,
        final_mix,
        ass,
        output,
        duration_seconds=6,
        width=320,
        height=568,
        preset="ultrafast",
    )
    probe = probe_media(output, ffprobe)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")

    assert video["codec_name"] == "h264"
    assert (video["width"], video["height"]) == (320, 568)
    assert audio["codec_name"] == "aac"
    assert audio["sample_rate"] == "48000"
    assert abs(float(probe["format"]["duration"]) - 6) < 0.2
