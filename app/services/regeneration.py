from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

from app.core.config import Settings
from app.database import Database, EpisodeRepository
from app.pipeline import DemoVideoPipeline
from app.pipeline.demo_video_pipeline import _visual_difference_score
from app.providers.image import PlaceholderImageProvider
from app.providers.video import LocalMotionVideoProvider
from app.quality import QualityInspector
from app.rendering.ffmpeg import resolve_media_tool
from app.rendering.final_renderer import render_final_video
from app.schemas.story import Story
from app.web.repository import WebRepository


PROTECTED_FILES = {
    "story.json",
    "character_bible.json",
    "metadata.json",
}
GENERATED_NAMES = {
    "images",
    "clips",
    "audio",
    "subtitles",
    "final_short.mp4",
    "quality_report.json",
}


class RegenerationService:
    def __init__(self, settings: Settings, repository: WebRepository):
        self.settings = settings
        self.repository = repository

    def regenerate_full(
        self, job_id: str, episode_id: str, progress
    ) -> Path:
        active = self.settings.output_dir / episode_id
        staging_root = self.settings.output_dir / ".staging" / job_id
        staging_episode = staging_root / episode_id
        archive = (
            self.settings.output_dir / ".archive" / episode_id / job_id
        )
        self._prepare_protected(active, staging_episode)
        story = Story.model_validate_json(
            (staging_episode / "story.json").read_text(encoding="utf-8")
        )
        temporary_settings = replace(
            self.settings,
            output_dir=staging_root,
            database_path=staging_root / "staging.db",
        )
        temporary_database = Database(temporary_settings.database_path)
        temporary_database.initialize()
        EpisodeRepository(temporary_database).save_story(
            story,
            str(staging_episode / "story.json"),
            "mock",
            f"{job_id}-staging",
        )
        result = DemoVideoPipeline(temporary_settings).run(
            episode_id, progress_callback=progress
        )
        report = json.loads(
            result.quality_report_path.read_text(encoding="utf-8")
        )
        if report["status"] != "passed":
            raise RuntimeError("Staging quality report did not pass.")
        mappings = self._promote_full(active, staging_episode, archive)
        self.repository.archive_asset_paths(episode_id, mappings)
        self._record_active_assets(episode_id, active)
        EpisodeRepository(self.repository.database).complete_stage_two(
            episode_id,
            str(active / "final_short.mp4"),
            str(active / "quality_report.json"),
            {
                "image": "placeholder",
                "video": "local_motion",
                "tts": result.tts_provider_used,
                "music": "generated_demo",
                "sound_effects": "generated_demo",
                "render": "ffmpeg",
            },
        )
        shutil.rmtree(staging_root, ignore_errors=True)
        return archive

    def regenerate_scene(
        self,
        job_id: str,
        episode_id: str,
        scene_number: int,
        progress,
    ) -> tuple[Path, dict[int, str], dict[int, str]]:
        active = self.settings.output_dir / episode_id
        staging_root = self.settings.output_dir / ".staging" / job_id
        staging_episode = staging_root / episode_id
        archive = (
            self.settings.output_dir / ".archive" / episode_id / job_id
        )
        if staging_episode.exists():
            shutil.rmtree(staging_episode)
        shutil.copytree(active, staging_episode)
        before = _scene_hashes(active)
        story = Story.model_validate_json(
            (staging_episode / "story.json").read_text(encoding="utf-8")
        )
        scene = story.scenes[scene_number - 1]
        progress("generating_images", 20)
        image = staging_episode / "images" / f"scene_{scene_number:02d}.png"
        PlaceholderImageProvider(
            self.settings.video_width, self.settings.video_height
        ).generate_scene(
            scene,
            story.character_bible.main_character,
            story.story_category,
            image,
        )
        progress("generating_clips", 45)
        ffmpeg = resolve_media_tool("ffmpeg", self.settings.ffmpeg_path)
        ffprobe = resolve_media_tool("ffprobe", self.settings.ffprobe_path)
        clip = staging_episode / "clips" / f"scene_{scene_number:02d}.mp4"
        LocalMotionVideoProvider(
            ffmpeg,
            self.settings.video_width,
            self.settings.video_height,
            self.settings.video_fps,
        ).generate_scene(
            image, clip, scene.duration_seconds, scene_number
        )
        clips = [
            staging_episode / "clips" / f"scene_{number:02d}.mp4"
            for number in range(1, 7)
        ]
        images = [
            staging_episode / "images" / f"scene_{number:02d}.png"
            for number in range(1, 7)
        ]
        progress("rendering_video", 80)
        render_final_video(
            ffmpeg,
            clips,
            staging_episode / "audio" / "final_mix.wav",
            staging_episode / "subtitles" / "subtitles.ass",
            staging_episode / "final_short.mp4",
            story.duration_target_seconds,
            self.settings.video_width,
            self.settings.video_height,
            self.settings.video_fps,
        )
        progress("quality_check", 95)
        report = QualityInspector(ffmpeg, ffprobe).inspect(
            episode_id,
            staging_episode / "final_short.mp4",
            story.duration_target_seconds,
            images,
            clips,
            staging_episode / "audio" / "narration.wav",
            staging_episode / "audio" / "music.wav",
            staging_episode / "subtitles" / "subtitles.srt",
            staging_episode / "subtitles" / "subtitles.ass",
            staging_episode / "quality_report.json",
            self.settings.video_width,
            self.settings.video_height,
            self.settings.video_fps,
            placeholder_contains_text=False,
            visual_difference_score=_visual_difference_score(images),
        )
        if report["status"] != "passed":
            raise RuntimeError("Scene staging quality report did not pass.")
        names = [
            f"images/scene_{scene_number:02d}.png",
            f"clips/scene_{scene_number:02d}.mp4",
            "final_short.mp4",
            "quality_report.json",
        ]
        mappings = self._promote_selected(
            active, staging_episode, archive, names
        )
        self.repository.archive_asset_paths(episode_id, mappings)
        self._record_active_assets(episode_id, active, scene_number)
        EpisodeRepository(self.repository.database).complete_stage_two(
            episode_id,
            str(active / "final_short.mp4"),
            str(active / "quality_report.json"),
            {
                "image": "placeholder",
                "video": "local_motion",
                "render": "ffmpeg",
            },
        )
        after = _scene_hashes(active)
        for number in range(1, 7):
            if number != scene_number and before[number] != after[number]:
                raise RuntimeError(
                    f"Scene {number} changed during scene regeneration."
                )
        shutil.rmtree(staging_root, ignore_errors=True)
        return archive, before, after

    def delete_generated_media(self, episode_id: str) -> list[str]:
        active = self.settings.output_dir / episode_id
        deleted = []
        for name in GENERATED_NAMES:
            path = active / name
            if path.is_dir():
                shutil.rmtree(path)
                deleted.append(name)
            elif path.is_file():
                path.unlink()
                deleted.append(name)
        self.repository.mark_media_deleted(episode_id)
        return sorted(deleted)

    def recover_staging(self) -> list[str]:
        staging = self.settings.output_dir / ".staging"
        interrupted = self.settings.output_dir / ".interrupted"
        recovered = []
        if not staging.is_dir():
            return recovered
        interrupted.mkdir(parents=True, exist_ok=True)
        for job_dir in staging.iterdir():
            if not job_dir.is_dir():
                continue
            target = interrupted / job_dir.name
            if target.exists():
                shutil.rmtree(target)
            job_dir.replace(target)
            recovered.append(job_dir.name)
        return recovered

    @staticmethod
    def _prepare_protected(active: Path, staging: Path) -> None:
        staging.mkdir(parents=True, exist_ok=False)
        for name in PROTECTED_FILES:
            source = active / name
            if not source.is_file():
                raise FileNotFoundError(f"Protected episode file missing: {source}")
            shutil.copy2(source, staging / name)

    @staticmethod
    def _promote_full(
        active: Path, staging: Path, archive: Path
    ) -> dict[str, str]:
        archive.mkdir(parents=True, exist_ok=False)
        mappings = {}
        moved_old = []
        moved_new = []
        try:
            for name in GENERATED_NAMES:
                current = active / name
                if current.exists():
                    destination = archive / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    current.replace(destination)
                    mappings[str(current)] = str(destination)
                    moved_old.append((destination, current))
            for name in GENERATED_NAMES:
                incoming = staging / name
                if incoming.exists():
                    destination = active / name
                    incoming.replace(destination)
                    moved_new.append((destination, incoming))
            return mappings
        except Exception:
            for destination, incoming in reversed(moved_new):
                if destination.exists():
                    destination.replace(incoming)
            for archived, current in reversed(moved_old):
                if archived.exists():
                    archived.replace(current)
            raise

    @staticmethod
    def _promote_selected(
        active: Path,
        staging: Path,
        archive: Path,
        names: list[str],
    ) -> dict[str, str]:
        archive.mkdir(parents=True, exist_ok=False)
        mappings = {}
        moved_old = []
        moved_new = []
        try:
            for name in names:
                current = active / name
                archived = archive / name
                archived.parent.mkdir(parents=True, exist_ok=True)
                if current.exists():
                    current.replace(archived)
                    mappings[str(current)] = str(archived)
                    moved_old.append((archived, current))
                incoming = staging / name
                incoming.replace(current)
                moved_new.append((current, incoming))
            return mappings
        except Exception:
            for current, incoming in reversed(moved_new):
                if current.exists():
                    current.replace(incoming)
            for archived, current in reversed(moved_old):
                if archived.exists():
                    archived.replace(current)
            raise

    def _record_active_assets(
        self,
        episode_id: str,
        active: Path,
        scene_number: int | None = None,
    ) -> None:
        repository = EpisodeRepository(self.repository.database)
        numbers = [scene_number] if scene_number else list(range(1, 7))
        for number in numbers:
            repository.record_asset(
                episode_id,
                "image",
                "placeholder",
                str(active / "images" / f"scene_{number:02d}.png"),
                number,
            )
            repository.record_asset(
                episode_id,
                "clip",
                "local_motion",
                str(active / "clips" / f"scene_{number:02d}.mp4"),
                number,
            )
        repository.record_asset(
            episode_id,
            "final_video",
            "ffmpeg",
            str(active / "final_short.mp4"),
        )
        repository.record_asset(
            episode_id,
            "quality_report",
            "ffprobe",
            str(active / "quality_report.json"),
        )


def _scene_hashes(directory: Path) -> dict[int, str]:
    result = {}
    for number in range(1, 7):
        digest = hashlib.sha256()
        for folder, extension in (("images", "png"), ("clips", "mp4")):
            path = directory / folder / f"scene_{number:02d}.{extension}"
            digest.update(path.read_bytes())
        result[number] = digest.hexdigest()
    return result
