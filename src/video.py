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
        image = project_dir / "scenes" / f"scene_{index:02d}.png"
        audio = project_dir / "audio" / f"scene_{index:02d}.wav"
        clip = clips_dir / f"clip_{index:02d}.mp4"
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

