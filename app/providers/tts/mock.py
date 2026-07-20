import math
from pathlib import Path
import struct
import wave

from app.providers.base import TTSProvider


class MockNarrationProvider(TTSProvider):
    """Create a quiet, timed narration placeholder without external services."""

    provider_name = "mock"

    def __init__(self, sample_rate: int = 48_000):
        self.sample_rate = sample_rate

    def synthesize(
        self, text: str, output_path: Path, duration_seconds: int
    ) -> Path:
        if duration_seconds < 1:
            raise ValueError("Narration duration must be positive.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        total_frames = self.sample_rate * duration_seconds
        word_density = max(1, min(8, len(text.split()) // 8))
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            frames = bytearray()
            for frame in range(total_frames):
                second = frame / self.sample_rate
                phase = second % 1.0
                active = phase < min(0.56, 0.18 + word_density * 0.045)
                envelope = (
                    math.sin(math.pi * phase / 0.56) ** 2
                    if active
                    else 0.0
                )
                frequency = 220 + 18 * math.sin(2 * math.pi * 0.7 * second)
                sample = int(
                    1900
                    * envelope
                    * math.sin(2 * math.pi * frequency * second)
                )
                frames.extend(struct.pack("<h", sample))
            output.writeframes(frames)
        temporary.replace(output_path)
        return output_path
