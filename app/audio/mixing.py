from pathlib import Path

from app.rendering.ffmpeg import run_checked


def mix_audio(
    ffmpeg_path: Path,
    narration_path: Path,
    music_path: Path,
    effects_path: Path,
    output_path: Path,
    duration_seconds: int,
    sample_rate: int = 48_000,
) -> Path:
    for path in (narration_path, music_path, effects_path):
        if not path.is_file():
            raise FileNotFoundError(f"Audio input not found: {path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    duration = str(duration_seconds)
    filter_graph = (
        f"[0:a]aresample={sample_rate},aformat=channel_layouts=stereo,"
        f"apad,atrim=0:{duration},volume=1.0[narr];"
        f"[1:a]aresample={sample_rate},aformat=channel_layouts=stereo,"
        f"apad,atrim=0:{duration},volume=0.16[music];"
        "[music][narr]sidechaincompress="
        "threshold=0.012:ratio=8:attack=20:release=450[ducked];"
        f"[2:a]aresample={sample_rate},aformat=channel_layouts=stereo,"
        f"apad,atrim=0:{duration},volume=0.16[sfx];"
        "[narr][ducked][sfx]amix=inputs=3:duration=longest:normalize=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.94,"
        f"atrim=0:{duration}[mixed]"
    )
    try:
        run_checked(
            [
                str(ffmpeg_path),
                "-y",
                "-i",
                str(narration_path),
                "-i",
                str(music_path),
                "-i",
                str(effects_path),
                "-filter_complex",
                filter_graph,
                "-map",
                "[mixed]",
                "-ar",
                str(sample_rate),
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(temporary),
            ],
            "Narration, music, and effects mix",
        )
        if not temporary.is_file() or temporary.stat().st_size <= 44:
            raise RuntimeError("Audio mixing produced an empty WAV file.")
        temporary.replace(output_path)
        return output_path
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
