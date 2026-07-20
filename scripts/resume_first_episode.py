from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from animation.models import SceneAnimation
from animation.runway_provider import RunwayVideoProvider
from src.character_design import CharacterDesignStore
from src.config import settings
from src.providers.media import RunwayReferenceImageProvider
from src.video import build_video


PROJECT = sorted(
    settings.projects_dir.glob("*-leo-meets-scout"),
    key=lambda path: path.stat().st_mtime,
)[-1]
MANIFEST = PROJECT / "scene_production_manifest.json"
PROGRESS = ROOT / "output" / "first_episode_resume_progress.jsonl"
START_SCENE = 4
END_SCENE = 17
MAX_ATTEMPTS = 3


def save_manifest(manifest: dict) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(MANIFEST)


def report(scene: int | None, status: str, **details) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "time": datetime.now(timezone.utc).isoformat(),
        "scene": scene,
        "status": status,
        **details,
    }
    with PROGRESS.open("a", encoding="utf-8") as output:
        output.write(json.dumps(payload, ensure_ascii=False) + "\n")


def retry_scene(number, record, master_prompt, duration, narration) -> None:
    image = PROJECT / "images" / f"scene_{number:02d}.png"
    animation_path = (
        PROJECT / "animated_clips" / f"scene_{number:02d}.mp4"
    )
    references = [
        ROOT / "assets" / "references" / "leo" / "leo_model_sheet.png",
        ROOT / "assets" / "references" / "scout" / "scout_model_sheet.png",
    ]
    image_provider = RunwayReferenceImageProvider(
        api_key=settings.runway_api_key,
        reference_images=references,
        model=settings.runway_image_model,
        ratio=settings.runway_ratio,
        poll_interval=settings.runway_poll_interval,
        timeout=settings.runway_timeout,
    )
    video_provider = RunwayVideoProvider.from_settings(settings)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        record["repair_attempts"] = attempt
        record["status"] = "generating_master"
        record["error"] = None
        save_manifest(manifest)
        try:
            image.unlink(missing_ok=True)
            image_provider.create_scene(
                master_prompt, image, f"SCENE {number}"
            )
            record["status"] = "master_ready"
            save_manifest(manifest)

            animation_path.unlink(missing_ok=True)
            animation = SceneAnimation(
                image_path=image,
                animation_prompt=(
                    "Continuous seamless shot. The characters make gentle, "
                    "controlled natural movements matching this moment. "
                    "Subtle facial expressions and soft forest motion."
                ),
                duration=duration,
                camera_motion="very slow stable cinematic push-in",
                output_video=animation_path,
                audio_path=PROJECT / "audio" / f"scene_{number:02d}.wav",
            )
            record["status"] = "generating"
            save_manifest(manifest)
            result = video_provider.generate_scene(animation)
            if result.status != "generated":
                raise RuntimeError(result.error or "Runway animation failed.")
            record["status"] = "completed"
            record["error"] = None
            record["master_frame"] = str(image)
            record["output_video"] = str(animation_path)
            save_manifest(manifest)
            report(number, "completed", attempt=attempt, duration=duration)
            return
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
            save_manifest(manifest)
            report(number, "retry", attempt=attempt, error=record["error"])
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(min(2**attempt, 10))


def create_audio_beds(duration_seconds: int) -> tuple[Path, Path]:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    ambience = PROJECT / "forest_ambience.mp3"
    music = PROJECT / "gentle_cinematic_music.mp3"
    ambience.write_bytes(
        b"".join(
            client.text_to_sound_effects.convert(
                text=(
                    "Gentle peaceful daytime forest ambience, soft leaves in "
                    "a light breeze, distant friendly birds, no voices, no "
                    "sudden loud sounds, seamless loop"
                ),
                duration_seconds=30,
                loop=True,
                output_format="mp3_44100_128",
            )
        )
    )
    music.write_bytes(
        b"".join(
            client.music.compose(
                prompt=(
                    "Warm gentle cinematic instrumental underscore for a "
                    "children's friendship story in a peaceful forest. Soft "
                    "piano, light strings and delicate woodwinds, hopeful and "
                    "tender, no vocals, no percussion hits, unobtrusive under "
                    "dialogue, smooth beginning and ending."
                ),
                music_length_ms=duration_seconds * 1000,
                force_instrumental=True,
                output_format="mp3_44100_128",
            )
        )
    )
    return ambience, music


def mix_audio(video: Path, ambience: Path, music: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for the final mix.")
    mixed = video.with_name("final_video.mixed.mp4")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-stream_loop",
            "-1",
            "-i",
            str(ambience),
            "-i",
            str(music),
            "-filter_complex",
            (
                "[0:a]volume=1.0[dialogue];"
                "[1:a]volume=0.10[ambience];"
                "[2:a]volume=0.07[music];"
                "[dialogue][ambience][music]"
                "amix=inputs=3:duration=first:normalize=0,"
                "alimiter=limit=0.95[audio]"
            ),
            "-map",
            "0:v:0",
            "-map",
            "[audio]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(mixed),
        ],
        check=True,
        capture_output=True,
    )
    mixed.replace(video)


metadata = json.loads((PROJECT / "metadata.json").read_text(encoding="utf-8"))
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
design_store = CharacterDesignStore(settings.character_designs_dir)

PROGRESS.unlink(missing_ok=True)
for number in range(START_SCENE, END_SCENE + 1):
    scene = metadata["scenes"][number - 1]
    record = manifest["scenes"][str(number)]
    # Only repair the known fallback range. Scenes 1-3 are never touched.
    retry_scene(
        number,
        record,
        design_store.build_scene_prompt(
            scene["visual_prompt"], scene["narration"]
        ),
        int(scene["duration_seconds"]),
        scene["narration"],
    )

video, message = build_video(PROJECT, len(metadata["scenes"]))
if video is None:
    raise RuntimeError(message)
ambience, music = create_audio_beds(120)
mix_audio(video, ambience, music)
report(None, "final_completed", video=str(video.resolve()))
