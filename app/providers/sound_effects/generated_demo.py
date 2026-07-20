import math
from pathlib import Path
import struct
import wave

from app.providers.base import SoundEffectProvider
from app.schemas.story import Scene


class GeneratedDemoSoundEffectProvider(SoundEffectProvider):
    provider_name = "generated_demo"

    def __init__(self, sample_rate: int = 48_000):
        self.sample_rate = sample_rate
        self.last_cues: list[dict[str, object]] = []

    def generate(
        self,
        scenes: list[Scene],
        output_path: Path,
        duration_seconds: int,
    ) -> Path:
        self.last_cues = []
        offset = 0.0
        for scene in scenes:
            if scene.sound_effects:
                self.last_cues.append(
                    {
                        "time_seconds": offset + 0.35,
                        "scene_number": scene.scene_number,
                        "labels": list(scene.sound_effects),
                    }
                )
            offset += scene.duration_seconds

        total_frames = self.sample_rate * duration_seconds
        samples = [0.0] * total_frames
        for cue_index, cue in enumerate(self.last_cues):
            start = int(float(cue["time_seconds"]) * self.sample_rate)
            effect_frames = min(
                int(0.32 * self.sample_rate), total_frames - start
            )
            frequency = 620 + (cue_index % 3) * 110
            for index in range(max(0, effect_frames)):
                envelope = (1 - index / max(1, effect_frames)) ** 2
                samples[start + index] += (
                    0.055
                    * envelope
                    * math.sin(
                        2 * math.pi * frequency * index / self.sample_rate
                    )
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            frames = bytearray()
            for value in samples:
                sample = int(max(-1.0, min(1.0, value)) * 32767)
                packed = struct.pack("<h", sample)
                frames.extend(packed)
                frames.extend(packed)
            output.writeframes(frames)
        temporary.replace(output_path)
        return output_path
