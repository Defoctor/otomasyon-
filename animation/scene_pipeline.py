from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from .models import AnimationResult, SceneAnimation
from .provider import VideoProvider


MasterFrameGenerator = Callable[["SceneProduction"], bool]


@dataclass(frozen=True)
class SceneProduction:
    number: int
    master_frame: Path
    master_prompt: str
    animation: SceneAnimation


class SceneProductionPipeline:
    """Resumable master-frame and independent scene-clip orchestrator."""

    def __init__(
        self,
        project_dir: Path,
        scenes: list[SceneProduction],
        max_attempts: int = 3,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.project_dir = project_dir
        self.scenes = scenes
        self.max_attempts = max_attempts
        self.manifest_path = project_dir / "scene_production_manifest.json"
        self._manifest = self._load_manifest()
        self._sync_scenes()

    def prepare_master_frames(
        self, generator: MasterFrameGenerator
    ) -> int:
        failures = 0
        for scene in self.scenes:
            record = self._record(scene.number)
            if self._valid_file(scene.master_frame):
                if record["status"] == "pending":
                    record["status"] = "master_ready"
                self._save()
                continue
            try:
                generator(scene)
                if not self._valid_file(scene.master_frame):
                    raise RuntimeError("Master frame was not created.")
                record["status"] = "master_ready"
                record["master_error"] = None
            except Exception as exc:
                failures += 1
                record["status"] = "failed"
                record["master_error"] = f"{type(exc).__name__}: {exc}"
            self._save()
        return failures

    def generate_clips(
        self, provider: VideoProvider | None
    ) -> list[AnimationResult]:
        if provider is None:
            return []
        results = []
        for scene in self.scenes:
            record = self._record(scene.number)
            if self._valid_file(scene.animation.output_video):
                record["status"] = "completed"
                record["error"] = None
                self._save()
                results.append(
                    AnimationResult(
                        scene.animation,
                        "generated",
                        ["resume", provider.provider_name],
                        scene.animation.output_video,
                    )
                )
                continue
            if not self._valid_file(scene.master_frame):
                record["status"] = "failed"
                record["error"] = "Master frame is missing."
                self._save()
                continue

            result = None
            for _ in range(self.max_attempts):
                record["attempts"] += 1
                record["status"] = "generating"
                self._save()
                result = provider.generate_scene(scene.animation)
                if (
                    result.status == "generated"
                    and self._valid_file(scene.animation.output_video)
                ):
                    record["status"] = "completed"
                    record["error"] = None
                    break
                record["status"] = "failed"
                record["error"] = result.error or "Video generation failed."
                self._save()
            if result is not None:
                results.append(result)
            self._save()
        return results

    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": 1, "scenes": {}}
        try:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "scenes": {}}
        return value if isinstance(value, dict) else {"version": 1, "scenes": {}}

    def _sync_scenes(self) -> None:
        records = self._manifest.setdefault("scenes", {})
        for scene in self.scenes:
            key = str(scene.number)
            records.setdefault(
                key,
                {
                    "number": scene.number,
                    "status": "pending",
                    "attempts": 0,
                    "master_frame": str(scene.master_frame),
                    "output_video": str(scene.animation.output_video),
                    "error": None,
                    "master_error": None,
                },
            )
        self._save()

    def _record(self, number: int) -> dict:
        return self._manifest["scenes"][str(number)]

    def _save(self) -> None:
        self._manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.manifest_path)

    @staticmethod
    def _valid_file(path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0
