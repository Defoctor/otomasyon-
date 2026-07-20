from pathlib import Path
import wave

from app.providers.music import GeneratedDemoMusicProvider
from app.providers.sound_effects import GeneratedDemoSoundEffectProvider
from app.providers.story import MockStoryProvider
from app.schemas.story import StoryCategory


def wave_details(path: Path) -> tuple[int, int, int]:
    with wave.open(str(path), "rb") as audio:
        return (
            audio.getframerate(),
            audio.getnchannels(),
            audio.getnframes(),
        )


def test_generated_music_is_stereo_48khz_and_timed(tmp_path: Path):
    output = tmp_path / "music.wav"

    GeneratedDemoMusicProvider().generate(
        "curious to uplifting", output, duration_seconds=2
    )

    assert wave_details(output) == (48_000, 2, 96_000)


def test_generated_sound_effects_reads_scene_metadata(tmp_path: Path):
    story = MockStoryProvider().generate(
        "episode_0001", StoryCategory.ANIMAL_RESCUE, 30, seed=9
    )
    output = tmp_path / "effects.wav"
    provider = GeneratedDemoSoundEffectProvider(sample_rate=8_000)

    provider.generate(story.scenes, output, duration_seconds=30)

    assert wave_details(output) == (8_000, 2, 240_000)
    assert len(provider.last_cues) == 6
    assert provider.last_cues[0]["labels"] == story.scenes[0].sound_effects
