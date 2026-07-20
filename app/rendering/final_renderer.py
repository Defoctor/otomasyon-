from pathlib import Path

from app.rendering.ffmpeg import run_checked


def render_final_video(
    ffmpeg_path: Path,
    clips: list[Path],
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    duration_seconds: int,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    preset: str = "veryfast",
) -> Path:
    if len(clips) != 6:
        raise ValueError(f"Final render requires exactly 6 clips; got {len(clips)}.")
    for path in [*clips, audio_path, ass_path]:
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Required render asset is missing: {path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_path = output_path.with_name("clips.concat.tmp.txt")
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    concat_path.write_text(
        "\n".join(f"file '{_concat_path(path)}'" for path in clips) + "\n",
        encoding="utf-8",
    )
    subtitle_filter = f"ass=filename='{_filter_path(ass_path)}'"
    try:
        run_checked(
            [
                str(ffmpeg_path),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-i",
                str(audio_path),
                "-vf",
                subtitle_filter,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                str(duration_seconds),
                "-r",
                str(fps),
                "-s",
                f"{width}x{height}",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-metadata",
                "comment=burned_subtitles:subtitles.ass",
                "-movflags",
                "+faststart",
                "-f",
                "mp4",
                str(temporary),
            ],
            "Final Shorts render",
        )
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError("Final render produced an empty MP4 file.")
        temporary.replace(output_path)
        return output_path
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        concat_path.unlink(missing_ok=True)


def _concat_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", r"'\''")


def _filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    value = value.replace("\\", "/").replace(":", r"\:")
    return value.replace("'", r"\'")
