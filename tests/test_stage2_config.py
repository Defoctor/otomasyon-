from app.core.config import Settings
from app.providers.base import (
    ImageProvider,
    MusicProvider,
    SoundEffectProvider,
    TTSProvider,
    VideoProvider,
)


def test_stage_two_provider_contracts_exist():
    assert ImageProvider.__abstractmethods__ == {"generate_scene"}
    assert VideoProvider.__abstractmethods__ == {"generate_scene"}
    assert TTSProvider.__abstractmethods__ == {"synthesize"}
    assert MusicProvider.__abstractmethods__ == {"generate"}
    assert SoundEffectProvider.__abstractmethods__ == {"generate"}


def test_stage_two_defaults_are_local_and_vertical(monkeypatch):
    for name in (
        "IMAGE_PROVIDER",
        "VIDEO_PROVIDER",
        "TTS_PROVIDER",
        "MUSIC_PROVIDER",
        "SOUND_EFFECT_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()

    assert settings.image_provider == "placeholder"
    assert settings.video_provider == "local_motion"
    assert settings.tts_provider == "local"
    assert settings.music_provider == "generated_demo"
    assert settings.sound_effect_provider == "generated_demo"
    assert (settings.video_width, settings.video_height) == (1080, 1920)
    assert settings.video_fps == 30
    assert settings.audio_sample_rate == 48_000
