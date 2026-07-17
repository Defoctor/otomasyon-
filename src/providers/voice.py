from abc import ABC, abstractmethod
from pathlib import Path
import wave


class VoiceProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, duration_seconds: int) -> Path:
        raise NotImplementedError


class FakeVoiceProvider(VoiceProvider):
    """Test için sessiz WAV oluşturur; ücretli servise çağrı yapmaz."""

    def synthesize(self, text: str, output_path: Path, duration_seconds: int) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 16_000
        with wave.open(str(output_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(sample_rate)
            audio.writeframes(b"\x00\x00" * sample_rate * duration_seconds)
        return output_path

