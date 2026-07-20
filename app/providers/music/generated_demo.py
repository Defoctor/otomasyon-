import math
from pathlib import Path
import struct
import wave

from app.providers.base import MusicProvider


class GeneratedDemoMusicProvider(MusicProvider):
    provider_name = "generated_demo"

    def __init__(self, sample_rate: int = 48_000):
        self.sample_rate = sample_rate

    def generate(
        self, mood: str, output_path: Path, duration_seconds: int
    ) -> Path:
        if duration_seconds < 1:
            raise ValueError("Music duration must be positive.")
        root, tempo = _mood_profile(mood)
        notes = [root, root * 1.25, root * 1.5, root * 2.0]
        beat_seconds = 60.0 / tempo
        total_frames = self.sample_rate * duration_seconds
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            frames = bytearray()
            for frame in range(total_frames):
                second = frame / self.sample_rate
                note_index = int(second / (beat_seconds * 2)) % len(notes)
                frequency = notes[note_index]
                fade = min(1.0, second / 1.2, (duration_seconds - second) / 1.2)
                pad = (
                    math.sin(2 * math.pi * frequency * second)
                    + 0.35 * math.sin(2 * math.pi * frequency * 0.5 * second)
                )
                shimmer = 0.18 * math.sin(
                    2 * math.pi * frequency * 2.0 * second
                )
                sample = int(1050 * max(0.0, fade) * (pad + shimmer))
                sample = max(-32767, min(32767, sample))
                packed = struct.pack("<h", sample)
                frames.extend(packed)
                frames.extend(packed)
            output.writeframes(frames)
        temporary.replace(output_path)
        return output_path


def _mood_profile(mood: str) -> tuple[float, int]:
    lowered = mood.casefold()
    if "uplift" in lowered or "happy" in lowered:
        return 261.63, 92
    if "emotional" in lowered or "gentle" in lowered:
        return 196.00, 66
    if "curious" in lowered or "myster" in lowered:
        return 220.00, 76
    return 233.08, 72
