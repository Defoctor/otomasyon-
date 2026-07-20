from abc import ABC, abstractmethod
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
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


class ElevenLabsVoiceProvider(VoiceProvider):
    """ElevenLabs Text-to-Speech API ile tam hikâye MP3'ü üretir."""

    def __init__(
        self,
        voice_id: str,
        model_id: str,
        output_format: str,
        client: Any | None = None,
    ):
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOICE_PROVIDER=elevenlabs için .env dosyasında "
                "ELEVENLABS_API_KEY tanımlanmalıdır."
            )
        if not self.voice_id:
            raise RuntimeError(
                "VOICE_PROVIDER=elevenlabs için .env dosyasında "
                "ELEVENLABS_VOICE_ID tanımlanmalıdır."
            )
        from elevenlabs.client import ElevenLabs

        self._client = ElevenLabs(api_key=api_key)
        return self._client

    def synthesize_story(self, text: str, output_path: Path) -> Path:
        audio = self._get_client().text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            output_format=self.output_format,
            text=text,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as output:
            for chunk in audio:
                if chunk:
                    output.write(chunk)
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("ElevenLabs boş ses yanıtı döndürdü.")
        return output_path

    def synthesize(
        self, text: str, output_path: Path, duration_seconds: int
    ) -> Path:
        return self.synthesize_story(text, output_path.with_suffix(".mp3"))


class ElevenLabsMultiVoiceProvider(ElevenLabsVoiceProvider):
    """Konuşma segmentlerini role göre farklı ElevenLabs sesleriyle üretir."""

    def __init__(
        self,
        voice_ids: dict[str, str],
        model_id: str,
        output_format: str,
        client: Any | None = None,
    ):
        missing = [role for role, voice_id in voice_ids.items() if not voice_id]
        if missing:
            raise RuntimeError(
                "Eksik ElevenLabs rol sesleri: " + ", ".join(sorted(missing))
            )
        self.voice_ids = voice_ids
        super().__init__(
            voice_id=voice_ids["narrator"],
            model_id=model_id,
            output_format=output_format,
            client=client,
        )

    def synthesize_dialogue(
        self,
        segments: list[dict[str, str]],
        output_path: Path,
        segments_dir: Path | None = None,
    ) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("Çoklu ses MP3 birleştirmesi için FFmpeg gerekir.")
        if not segments:
            raise RuntimeError("Seslendirilecek konuşma segmenti bulunamadı.")

        segments_dir = segments_dir or output_path.parent / "voice_segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        generated = []
        client = self._get_client()
        for index, segment in enumerate(segments, start=1):
            role = str(segment.get("speaker", "narrator")).strip().lower()
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            voice_id = self.voice_ids.get(role, self.voice_ids["narrator"])
            segment_path = segments_dir / f"{index:03d}_{role}.mp3"
            temporary = segment_path.with_suffix(".mp3.tmp")
            audio = client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=self.model_id,
                output_format=self.output_format,
                text=text,
            )
            with temporary.open("wb") as output:
                for chunk in audio:
                    if chunk:
                        output.write(chunk)
            if temporary.stat().st_size == 0:
                temporary.unlink()
                raise RuntimeError(f"{role} için ElevenLabs boş ses döndürdü.")
            temporary.replace(segment_path)
            generated.append(segment_path)

        concat_file = segments_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in generated),
            encoding="utf-8",
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Birleştirilen çoklu karakter sesi boş.")
        return output_path


def split_story_audio(
    story_audio: Path, scene_durations: list[int], audio_dir: Path
) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "ElevenLabs MP3'ünü video sahnelerine bölmek için FFmpeg ve FFprobe gerekir."
        )
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(story_audio),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    total_audio_seconds = float(probe.stdout.strip())
    total_weight = sum(scene_durations)
    audio_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    start = 0.0
    for index, weight in enumerate(scene_durations, start=1):
        duration = total_audio_seconds * weight / total_weight
        output = audio_dir / f"scene_{index:02d}.wav"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(story_audio),
                "-ar",
                "16000",
                "-ac",
                "1",
                str(output),
            ],
            check=True,
            capture_output=True,
        )
        outputs.append(output)
        start += duration
    return outputs
