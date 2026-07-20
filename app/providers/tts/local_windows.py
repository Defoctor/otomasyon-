import logging
from pathlib import Path
import subprocess
import wave

from app.providers.base import TTSProvider
from app.providers.tts.mock import MockNarrationProvider


LOGGER = logging.getLogger(__name__)

POWERSHELL_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$text = [System.IO.File]::ReadAllText($args[0], [System.Text.Encoding]::UTF8)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($args[2]) { $synth.SelectVoice($args[2]) }
    $synth.Rate = 1
    $synth.Volume = 100
    $synth.SetOutputToWaveFile($args[1])
    $synth.Speak($text)
} finally {
    $synth.Dispose()
}
""".strip()


class WindowsLocalTTSProvider(TTSProvider):
    provider_name = "local"

    def __init__(
        self,
        voice_name: str = "Microsoft Zira Desktop",
        sample_rate: int = 48_000,
        fallback: TTSProvider | None = None,
        runner=subprocess.run,
    ):
        self.voice_name = voice_name
        self.sample_rate = sample_rate
        self.fallback = fallback or MockNarrationProvider(sample_rate)
        self.runner = runner
        self.last_provider_used = self.provider_name
        self.last_error: str | None = None

    def synthesize(
        self, text: str, output_path: Path, duration_seconds: int
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text_path = output_path.with_suffix(".narration.txt.tmp")
        temporary = output_path.with_name(
            f"{output_path.stem}.tmp{output_path.suffix}"
        )
        text_path.write_text(text, encoding="utf-8")
        try:
            self.runner(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    POWERSHELL_SCRIPT,
                    str(text_path.resolve()),
                    str(temporary.resolve()),
                    self.voice_name,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=max(30, duration_seconds * 3),
            )
            self._validate_wave(temporary)
            temporary.replace(output_path)
            self.last_provider_used = self.provider_name
            self.last_error = None
            return output_path
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            self.last_error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning(
                "Local Windows TTS failed; using mock narration: %s",
                self.last_error,
            )
            self.last_provider_used = self.fallback.provider_name
            return self.fallback.synthesize(
                text, output_path, duration_seconds
            )
        finally:
            text_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_wave(path: Path) -> None:
        if not path.is_file() or path.stat().st_size <= 44:
            raise RuntimeError("Windows TTS produced an empty WAV file.")
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() < 1:
                raise RuntimeError("Windows TTS WAV contains no audio frames.")
