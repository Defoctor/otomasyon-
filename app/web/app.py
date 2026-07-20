from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import Settings
from app.database import Database
from app.rendering.ffmpeg import resolve_media_tool
from app.web.repository import WebRepository
from app.web.job_manager import JobManager
from app.web.routes import episodes, jobs, media, pages
from app.web.schemas import SystemStatusResponse
from app.web.services import EpisodeWebService


def create_web_app(
    settings: Settings | None = None,
    job_manager_factory=None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    if resolved_settings.web_host != "127.0.0.1":
        raise ValueError(
            "The web panel may only bind to 127.0.0.1."
        )
    manager_holder: dict[str, JobManager] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager = (
            job_manager_factory(resolved_settings, repository)
            if job_manager_factory
            else JobManager(resolved_settings, repository)
        )
        manager.recover()
        manager_holder["manager"] = manager
        app.state.job_manager = manager
        yield
        manager.shutdown(wait=False)

    application = FastAPI(
        title="Kids Shorts Automation",
        version="0.3.0",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    web_root = Path(__file__).resolve().parent
    database = Database(resolved_settings.database_path)
    database.initialize()
    repository = WebRepository(database, resolved_settings.output_dir)
    application.state.database = database
    application.state.web_repository = repository
    application.state.episode_service = EpisodeWebService(
        repository, resolved_settings.output_dir
    )
    application.state.templates = Jinja2Templates(
        directory=str(web_root / "templates")
    )

    def system_status() -> SystemStatusResponse:
        try:
            resolve_media_tool("ffmpeg", resolved_settings.ffmpeg_path)
            ffmpeg_ready = True
        except Exception:
            ffmpeg_ready = False
        try:
            resolve_media_tool("ffprobe", resolved_settings.ffprobe_path)
            ffprobe_ready = True
        except Exception:
            ffprobe_ready = False
        return SystemStatusResponse(
            status=(
                "ready" if ffmpeg_ready and ffprobe_ready else "degraded"
            ),
            ffmpeg=ffmpeg_ready,
            ffprobe=ffprobe_ready,
            providers={
                "story": resolved_settings.story_provider,
                "image": resolved_settings.image_provider,
                "video": resolved_settings.video_provider,
                "tts": resolved_settings.tts_provider,
                "music": resolved_settings.music_provider,
            },
            totals=repository.dashboard_counts(),
        )

    application.state.system_status = system_status
    application.mount(
        "/static",
        StaticFiles(directory=str(web_root / "static")),
        name="static",
    )
    application.include_router(pages.router)
    application.include_router(episodes.router)
    application.include_router(episodes.action_router)
    application.include_router(jobs.router)
    application.include_router(media.router)

    @application.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "host": resolved_settings.web_host}

    @application.get(
        "/api/system/status",
        response_model=SystemStatusResponse,
        tags=["system"],
    )
    def api_system_status() -> SystemStatusResponse:
        return system_status()

    return application
