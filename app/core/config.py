from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.exceptions import ConfigurationError


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(
        f"{name} must be true or false; received {raw!r}."
    )


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    demo_mode: bool
    story_provider: str
    output_dir: Path
    database_path: Path
    default_language: str
    default_story_category: str
    default_duration_seconds: int
    default_scene_count: int
    max_episode_cost_usd: float
    require_manual_approval: bool
    image_provider: str = "placeholder"
    video_provider: str = "local_motion"
    tts_provider: str = "local"
    music_provider: str = "generated_demo"
    sound_effect_provider: str = "generated_demo"
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    audio_sample_rate: int = 48_000
    local_tts_voice: str = "Microsoft Zira Desktop"
    subtitle_font: str = "Arial"
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    web_job_workers: int = 1
    web_poll_interval_ms: int = 1500

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            demo_mode=_boolean("DEMO_MODE", True),
            story_provider=os.getenv("STORY_PROVIDER", "mock").lower(),
            output_dir=ROOT / os.getenv("OUTPUT_DIR", "output"),
            database_path=ROOT / os.getenv(
                "DATABASE_PATH", "data/kids_shorts.db"
            ),
            default_language=os.getenv("DEFAULT_LANGUAGE", "en"),
            default_story_category=os.getenv(
                "DEFAULT_STORY_CATEGORY", "auto"
            ),
            default_duration_seconds=int(
                os.getenv("DEFAULT_DURATION_SECONDS", "30")
            ),
            default_scene_count=int(os.getenv("DEFAULT_SCENE_COUNT", "6")),
            max_episode_cost_usd=float(
                os.getenv("MAX_EPISODE_COST_USD", "0")
            ),
            require_manual_approval=_boolean(
                "REQUIRE_MANUAL_APPROVAL", True
            ),
            image_provider=os.getenv(
                "IMAGE_PROVIDER", "placeholder"
            ).lower(),
            video_provider=os.getenv(
                "VIDEO_PROVIDER", "local_motion"
            ).lower(),
            tts_provider=os.getenv("TTS_PROVIDER", "local").lower(),
            music_provider=os.getenv(
                "MUSIC_PROVIDER", "generated_demo"
            ).lower(),
            sound_effect_provider=os.getenv(
                "SOUND_EFFECT_PROVIDER", "generated_demo"
            ).lower(),
            ffmpeg_path=os.getenv("FFMPEG_PATH", ""),
            ffprobe_path=os.getenv("FFPROBE_PATH", ""),
            video_width=int(os.getenv("VIDEO_WIDTH", "1080")),
            video_height=int(os.getenv("VIDEO_HEIGHT", "1920")),
            video_fps=int(os.getenv("VIDEO_FPS", "30")),
            audio_sample_rate=int(
                os.getenv("AUDIO_SAMPLE_RATE", "48000")
            ),
            local_tts_voice=os.getenv(
                "LOCAL_TTS_VOICE", "Microsoft Zira Desktop"
            ),
            subtitle_font=os.getenv("SUBTITLE_FONT", "Arial"),
            web_host=os.getenv("WEB_HOST", "127.0.0.1"),
            web_port=int(os.getenv("WEB_PORT", "8000")),
            web_job_workers=int(os.getenv("WEB_JOB_WORKERS", "1")),
            web_poll_interval_ms=int(
                os.getenv("WEB_POLL_INTERVAL_MS", "1500")
            ),
        )
        if settings.default_scene_count != 6:
            raise ConfigurationError(
                "AŞAMA 1 requires DEFAULT_SCENE_COUNT=6."
            )
        if not 25 <= settings.default_duration_seconds <= 35:
            raise ConfigurationError(
                "DEFAULT_DURATION_SECONDS must be between 25 and 35."
            )
        if settings.story_provider != "mock" and settings.demo_mode:
            raise ConfigurationError(
                "DEMO_MODE=true only supports STORY_PROVIDER=mock."
            )
        if (settings.video_width, settings.video_height) != (1080, 1920):
            raise ConfigurationError(
                "Demo output must use VIDEO_WIDTH=1080 and VIDEO_HEIGHT=1920."
            )
        if settings.video_fps != 30:
            raise ConfigurationError("Demo output must use VIDEO_FPS=30.")
        if settings.audio_sample_rate != 48_000:
            raise ConfigurationError(
                "Demo output must use AUDIO_SAMPLE_RATE=48000."
            )
        if settings.web_host != "127.0.0.1":
            raise ConfigurationError(
                "WEB_HOST must be 127.0.0.1. External binding is disabled."
            )
        if not 1 <= settings.web_port <= 65535:
            raise ConfigurationError("WEB_PORT must be between 1 and 65535.")
        if settings.web_job_workers < 1:
            raise ConfigurationError("WEB_JOB_WORKERS must be at least 1.")
        return settings
