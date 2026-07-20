from pathlib import Path

from app.audio import mix_audio
from app.providers.music import GeneratedDemoMusicProvider
from app.providers.sound_effects import GeneratedDemoSoundEffectProvider
from app.providers.story import MockStoryProvider
from app.providers.tts import MockNarrationProvider
from app.rendering.ffmpeg import probe_media, resolve_media_tool
from app.schemas.story import StoryCategory


def test_audio_mix_is_stereo_48khz_and_target_duration(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=1
    )
    narration = tmp_path / "narration.wav"
    music = tmp_path / "music.wav"
    effects = tmp_path / "effects.wav"
    output = tmp_path / "final_mix.wav"
    MockNarrationProvider().synthesize("Test narration", narration, 2)
    GeneratedDemoMusicProvider().generate("uplifting", music, 2)
    GeneratedDemoSoundEffectProvider().generate(story.scenes, effects, 2)

    mix_audio(
        resolve_media_tool("ffmpeg"),
        narration,
        music,
        effects,
        output,
        duration_seconds=2,
    )
    probe = probe_media(output, resolve_media_tool("ffprobe"))
    audio = next(
        stream for stream in probe["streams"] if stream["codec_type"] == "audio"
    )

    assert audio["sample_rate"] == "48000"
    assert audio["channels"] == 2
    assert abs(float(probe["format"]["duration"]) - 2.0) < 0.1
