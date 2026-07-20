from pathlib import Path
import shutil
import subprocess


def build_video(project_dir: Path, scene_count: int) -> tuple[Path | None, str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None, "FFmpeg bulunamadı. Görseller, sesler ve proje dosyaları hazırlandı."

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    clips = []
    for index in range(1, scene_count + 1):
        animated_clip = (
            project_dir / "animated_clips" / f"scene_{index:02d}.mp4"
        )
        image = project_dir / "images" / f"scene_{index:02d}.png"
        audio = project_dir / "audio" / f"scene_{index:02d}.wav"
        clip = clips_dir / f"clip_{index:02d}.mp4"
        if animated_clip.exists() and animated_clip.stat().st_size > 0:
            command = [
                ffmpeg, "-y", "-i", str(animated_clip), "-i", str(audio),
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
                "-pix_fmt", "yuv420p", "-shortest", str(clip),
            ]
        else:
            command = [
                ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
                "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
                "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest", str(clip),
            ]
        subprocess.run(command, check=True, capture_output=True)
        clips.append(clip)

    concat_file = clips_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{clip.as_posix()}'" for clip in clips),
        encoding="utf-8",
    )
    output = project_dir / "final_video.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", str(output)],
        check=True,
        capture_output=True,
    )
    return output, "Video FFmpeg ile oluşturuldu."


def build_short_video(
    project_dir: Path, video_path: Path | None
) -> tuple[Path | None, str]:
    if video_path is None or not video_path.exists():
        return None, "Ana video olmadığı için Shorts videosu oluşturulamadı."
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None, "FFmpeg bulunamadığı için Shorts videosu oluşturulamadı."

    output = project_dir / "shorts_video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-t",
            "60",
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output, "60 saniyelik dikey Shorts videosu oluşturuldu."
