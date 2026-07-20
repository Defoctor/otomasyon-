from pathlib import Path
import subprocess
import wave

from app.providers.tts import MockNarrationProvider, WindowsLocalTTSProvider


def test_mock_narration_creates_timed_wave(tmp_path: Path):
    output = tmp_path / "narration.wav"

    MockNarrationProvider(sample_rate=8_000).synthesize(
        "A gentle test narration.", output, duration_seconds=2
    )

    with wave.open(str(output), "rb") as audio:
        assert audio.getframerate() == 8_000
        assert audio.getnchannels() == 1
        assert audio.getnframes() == 16_000


def test_local_tts_failure_uses_mock_fallback(tmp_path: Path):
    def failing_runner(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "powershell.exe")

    output = tmp_path / "narration.wav"
    provider = WindowsLocalTTSProvider(
        sample_rate=8_000,
        fallback=MockNarrationProvider(8_000),
        runner=failing_runner,
    )

    provider.synthesize("Fallback narration.", output, 1)

    assert output.stat().st_size > 44
    assert provider.last_provider_used == "mock"
    assert "CalledProcessError" in provider.last_error


def test_microsoft_zira_local_tts_creates_wave_or_safe_fallback(tmp_path: Path):
    output = tmp_path / "zira.wav"
    provider = WindowsLocalTTSProvider()

    provider.synthesize(
        "A warm little story begins in a colorful forest.",
        output,
        duration_seconds=4,
    )

    assert output.stat().st_size > 44
    assert provider.last_provider_used in {"local", "mock"}
    if provider.last_provider_used == "mock":
        assert provider.last_error is not None
