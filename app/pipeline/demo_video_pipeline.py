from dataclasses import dataclass
import json
import logging
from pathlib import Path
import time
from collections.abc import Callable

from PIL import Image, ImageChops, ImageStat

from app.audio import mix_audio
from app.core.config import Settings
from app.database import Database, EpisodeRepository
from app.providers.image import PlaceholderImageProvider
from app.providers.music import GeneratedDemoMusicProvider
from app.providers.sound_effects import GeneratedDemoSoundEffectProvider
from app.providers.tts import WindowsLocalTTSProvider
from app.providers.video import LocalMotionVideoProvider
from app.quality import QualityInspector
from app.rendering.ffmpeg import resolve_media_tool
from app.rendering.final_renderer import render_final_video
from app.rendering.subtitles import create_subtitles
from app.schemas.story import Story


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoVideoResult:
    episode_id: str
    episode_directory: Path
    images_directory: Path
    clips_directory: Path
    narration_path: Path
    music_path: Path
    effects_path: Path
    final_mix_path: Path
    subtitles_directory: Path
    final_video_path: Path
    quality_report_path: Path
    database_path: Path
    render_seconds: float
    tts_provider_used: str


class DemoVideoPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings.database_path)
        self.repository = EpisodeRepository(self.database)

    def run(
        self,
        episode_id: str,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> DemoVideoResult:
        progress = progress_callback or (lambda stage, percent: None)
        started = time.perf_counter()
        self.database.initialize()
        episode_directory = self.settings.output_dir / episode_id
        story_path = episode_directory / "story.json"
        if not story_path.is_file():
            raise FileNotFoundError(f"Story JSON not found: {story_path}")
        story = Story.model_validate_json(
            story_path.read_text(encoding="utf-8")
        )
        if story.episode_id != episode_id:
            raise ValueError(
                f"Episode mismatch: requested {episode_id}, story contains "
                f"{story.episode_id}."
            )
        if self.repository.get_episode(episode_id) is None:
            raise RuntimeError(
                f"Episode {episode_id} is not registered in SQLite."
            )

        ffmpeg = resolve_media_tool("ffmpeg", self.settings.ffmpeg_path)
        ffprobe = resolve_media_tool("ffprobe", self.settings.ffprobe_path)
        self.repository.start_stage_two(episode_id)
        try:
            progress("generating_images", 15)
            images_directory = episode_directory / "images"
            clips_directory = episode_directory / "clips"
            audio_directory = episode_directory / "audio"
            subtitles_directory = episode_directory / "subtitles"
            image_provider = PlaceholderImageProvider(
                self.settings.video_width, self.settings.video_height
            )
            images = []
            for scene in story.scenes:
                output = images_directory / f"scene_{scene.scene_number:02d}.png"
                image_provider.generate_scene(
                    scene,
                    story.character_bible.main_character,
                    story.story_category,
                    output,
                )
                images.append(output)
                self.repository.record_asset(
                    episode_id,
                    "image",
                    image_provider.provider_name,
                    str(output),
                    scene.scene_number,
                )

            video_provider = LocalMotionVideoProvider(
                ffmpeg,
                self.settings.video_width,
                self.settings.video_height,
                self.settings.video_fps,
            )
            clips = []
            progress("generating_clips", 35)
            for scene, image in zip(story.scenes, images):
                output = clips_directory / f"scene_{scene.scene_number:02d}.mp4"
                video_provider.generate_scene(
                    image,
                    output,
                    scene.duration_seconds,
                    scene.scene_number,
                )
                clips.append(output)
                self.repository.record_asset(
                    episode_id,
                    "clip",
                    video_provider.provider_name,
                    str(output),
                    scene.scene_number,
                )

            narration_path = audio_directory / "narration.wav"
            progress("generating_narration", 50)
            narration_text = " ".join(scene.narration for scene in story.scenes)
            tts_provider = WindowsLocalTTSProvider(
                self.settings.local_tts_voice,
                self.settings.audio_sample_rate,
            )
            tts_provider.synthesize(
                narration_text,
                narration_path,
                story.duration_target_seconds,
            )
            self.repository.record_asset(
                episode_id,
                "narration",
                tts_provider.last_provider_used,
                str(narration_path),
            )

            music_path = audio_directory / "music.wav"
            progress("generating_music", 58)
            music_provider = GeneratedDemoMusicProvider(
                self.settings.audio_sample_rate
            )
            music_provider.generate(
                story.music_mood,
                music_path,
                story.duration_target_seconds,
            )
            self.repository.record_asset(
                episode_id,
                "music",
                music_provider.provider_name,
                str(music_path),
            )

            effects_path = audio_directory / "effects.wav"
            effects_provider = GeneratedDemoSoundEffectProvider(
                self.settings.audio_sample_rate
            )
            effects_provider.generate(
                story.scenes,
                effects_path,
                story.duration_target_seconds,
            )
            self.repository.record_asset(
                episode_id,
                "sound_effects",
                effects_provider.provider_name,
                str(effects_path),
            )
            cues_path = audio_directory / "sound_effects.json"
            _atomic_json(cues_path, {"cues": effects_provider.last_cues})
            self.repository.record_asset(
                episode_id,
                "sound_effect_metadata",
                effects_provider.provider_name,
                str(cues_path),
            )

            srt_path = subtitles_directory / "subtitles.srt"
            progress("generating_subtitles", 65)
            ass_path = subtitles_directory / "subtitles.ass"
            create_subtitles(
                story.scenes,
                srt_path,
                ass_path,
                self.settings.video_width,
                self.settings.video_height,
                self.settings.subtitle_font,
            )
            for subtitle in (srt_path, ass_path):
                self.repository.record_asset(
                    episode_id,
                    "subtitle",
                    "local",
                    str(subtitle),
                )

            final_mix_path = audio_directory / "final_mix.wav"
            progress("mixing_audio", 72)
            mix_audio(
                ffmpeg,
                narration_path,
                music_path,
                effects_path,
                final_mix_path,
                story.duration_target_seconds,
                self.settings.audio_sample_rate,
            )
            self.repository.record_asset(
                episode_id,
                "audio_mix",
                "ffmpeg",
                str(final_mix_path),
            )

            final_video_path = episode_directory / "final_short.mp4"
            progress("rendering_video", 82)
            render_final_video(
                ffmpeg,
                clips,
                final_mix_path,
                ass_path,
                final_video_path,
                story.duration_target_seconds,
                self.settings.video_width,
                self.settings.video_height,
                self.settings.video_fps,
            )
            self.repository.record_asset(
                episode_id,
                "final_video",
                "ffmpeg",
                str(final_video_path),
            )

            report_path = episode_directory / "quality_report.json"
            progress("quality_check", 95)
            report = QualityInspector(ffmpeg, ffprobe).inspect(
                episode_id,
                final_video_path,
                story.duration_target_seconds,
                images,
                clips,
                narration_path,
                music_path,
                srt_path,
                ass_path,
                report_path,
                self.settings.video_width,
                self.settings.video_height,
                self.settings.video_fps,
                placeholder_contains_text=image_provider.contains_text,
                visual_difference_score=_visual_difference_score(images),
            )
            self.repository.record_asset(
                episode_id,
                "quality_report",
                "ffprobe",
                str(report_path),
                status=report["status"],
            )
            if report["status"] != "passed":
                raise RuntimeError(
                    "Critical quality checks failed: "
                    + "; ".join(report["critical_errors"])
                )

            providers = {
                "image": image_provider.provider_name,
                "video": video_provider.provider_name,
                "tts": tts_provider.last_provider_used,
                "music": music_provider.provider_name,
                "sound_effects": effects_provider.provider_name,
                "render": "ffmpeg",
            }
            self.repository.complete_stage_two(
                episode_id,
                str(final_video_path),
                str(report_path),
                providers,
            )
            metadata_path = episode_directory / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["providers_used"].update(providers)
            metadata["generation_status"] = "completed"
            metadata["approval_status"] = "pending"
            metadata["upload_status"] = "not_ready"
            metadata["final_video_path"] = str(final_video_path)
            metadata["generation_cost_estimate_usd"] = 0.0
            _atomic_json(metadata_path, metadata)

            return DemoVideoResult(
                episode_id=episode_id,
                episode_directory=episode_directory,
                images_directory=images_directory,
                clips_directory=clips_directory,
                narration_path=narration_path,
                music_path=music_path,
                effects_path=effects_path,
                final_mix_path=final_mix_path,
                subtitles_directory=subtitles_directory,
                final_video_path=final_video_path,
                quality_report_path=report_path,
                database_path=self.database.path,
                render_seconds=time.perf_counter() - started,
                tts_provider_used=tts_provider.last_provider_used,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("AŞAMA 2 failed for %s", episode_id)
            self.repository.fail_stage_two(episode_id, message)
            raise


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _visual_difference_score(images: list[Path]) -> float:
    prepared = []
    for path in images:
        with Image.open(path) as image:
            prepared.append(
                image.convert("RGB").resize((90, 160)).copy()
            )
    if len(prepared) < 2:
        return 0.0
    scores = []
    for first, second in zip(prepared, prepared[1:]):
        difference = ImageChops.difference(first, second)
        mean = ImageStat.Stat(difference).mean
        scores.append(sum(mean) / (len(mean) * 255))
    return sum(scores) / len(scores)
