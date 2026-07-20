from datetime import datetime
import json
from pathlib import Path
import re

from src.config import settings
from src.character_design import CharacterDesignStore
from src.memory import MemoryStore
from src.providers import (
    ElevenLabsMultiVoiceProvider,
    ElevenLabsVoiceProvider,
    FakeContentProvider,
    FakeMediaProvider,
    FakeVoiceProvider,
    OpenAIContentProvider,
    OpenAIImageProvider,
    RunwayReferenceImageProvider,
)
from src.providers.voice import split_story_audio
from src.thumbnail import create_thumbnail
from src.video import build_short_video, build_video
from src.youtube_upload import prepare_upload_package
from animation.factory import create_video_provider
from animation.models import SceneAnimation
from animation.prompts import DEFAULT_CAMERA_MOTION
from animation.scene_pipeline import SceneProduction, SceneProductionPipeline
from src.scene_planner import split_into_short_scenes


def load_topics() -> list[dict]:
    return json.loads(settings.topics_file.read_text(encoding="utf-8"))


def get_content_provider():
    provider = settings.content_provider.strip().lower()
    memory_store = MemoryStore(settings.memory_dir)
    if provider == "fake":
        return FakeContentProvider(memory_store=memory_store)
    if provider == "openai":
        return OpenAIContentProvider(
            model=settings.openai_model,
            memory_store=memory_store,
        )
    raise ValueError(
        f"Desteklenmeyen CONTENT_PROVIDER: {settings.content_provider!r}. "
        "'fake' veya 'openai' kullanın."
    )


def get_media_provider():
    provider = settings.media_provider.strip().lower()
    if provider == "fake":
        return FakeMediaProvider()
    if provider == "openai":
        return OpenAIImageProvider(
            model=settings.openai_image_model,
            size=settings.openai_image_size,
            quality=settings.openai_image_quality,
        )
    if provider in {"runway", "runway_references"}:
        references = [
            Path(value.strip())
            for value in settings.runway_reference_images.split(",")
            if value.strip()
        ]
        return RunwayReferenceImageProvider(
            api_key=settings.runway_api_key,
            reference_images=references,
            model=settings.runway_image_model,
            ratio=settings.runway_ratio,
            poll_interval=settings.runway_poll_interval,
            timeout=settings.runway_timeout,
        )
    raise ValueError(
        f"Desteklenmeyen MEDIA_PROVIDER: {settings.media_provider!r}. "
        "'fake' veya 'openai' kullanın."
    )


def get_voice_provider():
    provider = settings.voice_provider.strip().lower()
    if provider == "fake":
        return FakeVoiceProvider()
    if provider == "elevenlabs":
        return ElevenLabsVoiceProvider(
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model,
            output_format=settings.elevenlabs_output_format,
        )
    if provider == "elevenlabs_multi":
        return ElevenLabsMultiVoiceProvider(
            voice_ids=settings.elevenlabs_voice_ids,
            model_id=settings.elevenlabs_model,
            output_format=settings.elevenlabs_output_format,
        )
    raise ValueError(
        f"Desteklenmeyen VOICE_PROVIDER: {settings.voice_provider!r}. "
        "'fake', 'elevenlabs' veya 'elevenlabs_multi' kullanın."
    )


def create_scene_image_safely(
    media,
    fallback,
    prompt: str,
    output_path: Path,
    label: str,
    error_log: Path,
) -> bool:
    try:
        media.create_scene(prompt, output_path, label)
        return True
    except Exception as exc:
        error_log.parent.mkdir(parents=True, exist_ok=True)
        with error_log.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {
                        "scene": label,
                        "provider": type(media).__name__,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        fallback.create_scene(prompt, output_path, f"{label} - FALLBACK")
        return False


def run_pipeline(topic: dict, target_minutes: int = 5) -> dict:
    content = get_content_provider().generate(topic, target_minutes)
    content = split_into_short_scenes(
        content,
        minimum_seconds=settings.scene_min_duration,
        maximum_seconds=settings.scene_max_duration,
    )
    memory_store = MemoryStore(settings.memory_dir)
    design_store = CharacterDesignStore(settings.character_designs_dir)
    design_store.sync_from_memory(memory_store.load_all())
    slug = re.sub(r"[^a-z0-9]+", "-", topic["id"].lower()).strip("-")
    project_dir = settings.projects_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    project_dir.mkdir(parents=True, exist_ok=False)

    (project_dir / "metadata.json").write_text(
        json.dumps(content.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (project_dir / "script.txt").write_text(content.script, encoding="utf-8")
    (project_dir / "approval_status.json").write_text(
        json.dumps(
            {"approved": False, "youtube_uploaded": False, "note": "İnsan kontrolü bekleniyor."},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    media = get_media_provider()
    fallback_media = FakeMediaProvider()
    image_failures = 0
    productions = [
        SceneProduction(
            number=scene.number,
            master_frame=(
                project_dir / "images" / f"scene_{scene.number:02d}.png"
            ),
            master_prompt=design_store.build_scene_prompt(
                scene.visual_prompt, scene.narration
            ),
            animation=SceneAnimation(
                image_path=(
                    project_dir / "images" / f"scene_{scene.number:02d}.png"
                ),
                animation_prompt=(
                    "Continuous seamless shot. Gentle controlled character "
                    "movement and natural expressions. Subtle environmental "
                    "motion."
                ),
                duration=scene.duration_seconds,
                camera_motion=DEFAULT_CAMERA_MOTION,
                output_video=(
                    project_dir
                    / "animated_clips"
                    / f"scene_{scene.number:02d}.mp4"
                ),
                audio_path=(
                    project_dir / "audio" / f"scene_{scene.number:02d}.wav"
                ),
            ),
        )
        for scene in content.scenes
    ]
    scene_pipeline = SceneProductionPipeline(
        project_dir,
        productions,
        max_attempts=settings.scene_generation_attempts,
    )

    def create_master_frame(production: SceneProduction) -> bool:
        nonlocal image_failures
        image_created = create_scene_image_safely(
            media,
            fallback_media,
            production.master_prompt,
            production.master_frame,
            f"SAHNE {production.number}",
            project_dir / "image_generation_errors.jsonl",
        )
        if not image_created:
            image_failures += 1
        return image_created

    scene_pipeline.prepare_master_frames(create_master_frame)

    voice = get_voice_provider()
    narration_path = None
    if isinstance(voice, ElevenLabsMultiVoiceProvider):
        speech = [
            segment
            for scene in content.scenes
            for segment in (
                scene.speech
                or [{"speaker": "narrator", "text": scene.narration}]
            )
        ]
        narration_path = voice.synthesize_dialogue(
            speech,
            project_dir / "narration.mp3",
            project_dir / "voice_segments",
        )
        split_story_audio(
            narration_path,
            [scene.duration_seconds for scene in content.scenes],
            project_dir / "audio",
        )
    elif isinstance(voice, ElevenLabsVoiceProvider):
        narration_path = voice.synthesize_story(content.script, project_dir / "narration.mp3")
        split_story_audio(
            narration_path,
            [scene.duration_seconds for scene in content.scenes],
            project_dir / "audio",
        )
    else:
        for scene in content.scenes:
            voice.synthesize(
                scene.narration,
                project_dir / "audio" / f"scene_{scene.number:02d}.wav",
                scene.duration_seconds,
            )

    animation_results = []
    video_provider = create_video_provider(settings)
    if video_provider is not None:
        animation_results = scene_pipeline.generate_clips(video_provider)
        failures = [
            {
                "scene": result.scene.output_video.stem,
                "error": result.error,
            }
            for result in animation_results
            if result.status == "failed"
        ]
        if failures:
            (project_dir / "animation_errors.json").write_text(
                json.dumps(failures, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    video_path, message = build_video(project_dir, len(content.scenes))
    create_thumbnail(content.title, project_dir / "thumbnail.png")
    shorts_path, shorts_message = build_short_video(project_dir, video_path)
    youtube_package = prepare_upload_package(
        project_dir,
        content,
        video_path,
        shorts_path,
    )
    return {
        "project_dir": project_dir,
        "content": content,
        "video_path": video_path,
        "message": message,
        "image_failures": image_failures,
        "shorts_path": shorts_path,
        "shorts_message": shorts_message,
        "youtube_package": youtube_package,
        "narration_path": narration_path,
        "animation_results": animation_results,
        "scene_manifest": scene_pipeline.manifest_path,
    }
