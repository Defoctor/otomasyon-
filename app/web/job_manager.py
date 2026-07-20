from concurrent.futures import Future, ThreadPoolExecutor
import hashlib
import json
import logging
from threading import Lock
from typing import Callable

from app.core.config import Settings
from app.pipeline import DemoVideoPipeline, StoryPipeline
from app.web.repository import WebRepository
from app.web.schemas import GenerateEpisodeRequest, JobResponse
from app.services.regeneration import RegenerationService


LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[str, int], None]
WorkHandler = Callable[[str, str, dict, ProgressCallback], str | None]


class JobManager:
    def __init__(
        self,
        settings: Settings,
        repository: WebRepository,
        work_handler: WorkHandler | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.executor = ThreadPoolExecutor(
            max_workers=settings.web_job_workers,
            thread_name_prefix="kids-shorts-worker",
        )
        self.work_handler = work_handler or self._default_handler
        self.regeneration = RegenerationService(settings, repository)
        self._futures: dict[str, Future] = {}
        self._lock = Lock()

    def recover(self) -> int:
        recovered = self.repository.recover_interrupted_jobs()
        self.regeneration.recover_staging()
        return recovered

    def submit_generate(
        self, request: GenerateEpisodeRequest
    ) -> JobResponse:
        payload = request.model_dump(mode="json")
        # Each submission is a distinct attempt. Active-episode locking is
        # enforced by the repository; a historical identical request must not
        # permanently block a retry.
        key = _idempotency_key("generate", payload, unique=True)
        job = self.repository.create_job(
            "generate", request.episode_id, key
        )
        self._submit(job.job_id, "generate", payload)
        return job

    def submit_operation(
        self,
        job_type: str,
        episode_id: str,
        payload: dict | None = None,
        scene_number: int | None = None,
        staging_directory: str | None = None,
    ) -> JobResponse:
        data = payload or {}
        key = _idempotency_key(
            job_type,
            {
                "episode_id": episode_id,
                "scene_number": scene_number,
                **data,
            },
            unique=True,
        )
        job = self.repository.create_job(
            job_type,
            episode_id,
            key,
            scene_number=scene_number,
            staging_directory=staging_directory,
        )
        self._submit(job.job_id, job_type, data)
        return job

    def shutdown(self, wait: bool = False) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=False)

    def _submit(self, job_id: str, job_type: str, payload: dict) -> None:
        with self._lock:
            self._futures[job_id] = self.executor.submit(
                self._execute, job_id, job_type, payload
            )

    def _execute(self, job_id: str, job_type: str, payload: dict) -> None:
        def progress(stage: str, percent: int) -> None:
            self.repository.update_job(
                job_id,
                status="running",
                stage=stage,
                progress=percent,
            )

        try:
            progress("queued", 1)
            episode_id = self.work_handler(
                job_id, job_type, payload, progress
            )
            if episode_id:
                self.repository.bind_job_episode(job_id, episode_id)
            self.repository.update_job(
                job_id,
                status="waiting_for_approval",
                stage="waiting_for_approval",
                progress=100,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("Background job %s failed", job_id)
            self.repository.update_job(
                job_id,
                status="failed",
                stage="failed",
                progress=100,
                error=message,
            )

    def _default_handler(
        self,
        job_id: str,
        job_type: str,
        payload: dict,
        progress: ProgressCallback,
    ) -> str:
        if job_type == "regenerate_full":
            episode_id = str(payload["episode_id"])
            archive = self.regeneration.regenerate_full(
                job_id, episode_id, progress
            )
            self.repository.update_job(
                job_id,
                status="running",
                stage="quality_check",
                progress=99,
                archive_directory=str(archive),
            )
            return episode_id
        if job_type == "regenerate_scene":
            episode_id = str(payload["episode_id"])
            archive, _, _ = self.regeneration.regenerate_scene(
                job_id,
                episode_id,
                int(payload["scene_number"]),
                progress,
            )
            self.repository.update_job(
                job_id,
                status="running",
                stage="quality_check",
                progress=99,
                archive_directory=str(archive),
            )
            return episode_id
        if job_type != "generate":
            raise RuntimeError(f"Unsupported job type: {job_type}")
        request = GenerateEpisodeRequest.model_validate(payload)
        if request.create_story:
            progress("generating_story", 5)
            story_result = StoryPipeline(self.settings).run(
                category=(
                    None if request.automatic_category else request.category
                ),
                duration_seconds=request.duration_seconds,
                seed=request.seed,
            )
            episode_id = story_result.episode_id
            self.repository.bind_job_episode(job_id, episode_id)
        else:
            episode_id = str(request.episode_id)
        DemoVideoPipeline(self.settings).run(
            episode_id, progress_callback=progress
        )
        return episode_id


def _idempotency_key(
    job_type: str, payload: dict, unique: bool = False
) -> str:
    value = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    if unique:
        from uuid import uuid4

        value += uuid4().hex
    return hashlib.sha256(f"{job_type}:{value}".encode("utf-8")).hexdigest()
