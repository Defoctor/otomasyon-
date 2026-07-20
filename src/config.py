from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    content_provider: str = os.getenv("CONTENT_PROVIDER", "fake")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    openai_image_size: str = os.getenv("OPENAI_IMAGE_SIZE", "1536x1024")
    openai_image_quality: str = os.getenv("OPENAI_IMAGE_QUALITY", "medium")
    voice_provider: str = os.getenv("VOICE_PROVIDER", "fake")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "")
    elevenlabs_model: str = os.getenv(
        "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"
    )
    elevenlabs_output_format: str = os.getenv(
        "ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128"
    )
    elevenlabs_voice_ids: dict[str, str] = None
    media_provider: str = os.getenv("MEDIA_PROVIDER", "fake")
    youtube_upload_enabled: bool = (
        os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true"
    )
    projects_dir: Path = ROOT / "data" / "projects"
    topics_file: Path = ROOT / "data" / "topics.json"
    memory_dir: Path = ROOT / "memory"
    character_designs_dir: Path = ROOT / "assets" / "characters"
    enable_higgsfield: bool = (
        os.getenv("ENABLE_HIGGSFIELD", "false").lower() == "true"
    )
    video_provider: str = os.getenv(
        "VIDEO_PROVIDER",
        (
            "higgsfield"
            if os.getenv("ENABLE_HIGGSFIELD", "false").lower() == "true"
            else "none"
        ),
    )
    higgsfield_dry_run: bool = (
        os.getenv("HIGGSFIELD_DRY_RUN", "true").lower() == "true"
    )
    higgsfield_lip_sync: bool = (
        os.getenv("HIGGSFIELD_LIP_SYNC", "true").lower() == "true"
    )
    higgsfield_api_key: str = os.getenv("HIGGSFIELD_API_KEY", "")
    higgsfield_model: str = os.getenv("HIGGSFIELD_MODEL", "kling3_0")
    higgsfield_output_dir: Path = Path(
        os.getenv("HIGGSFIELD_OUTPUT_DIR", str(ROOT / "data" / "animations"))
    )
    higgsfield_cli_command: str = os.getenv(
        "HIGGSFIELD_CLI_COMMAND", "higgsfield"
    )
    runway_api_key: str = os.getenv("RUNWAY_API_KEY", "")
    runway_model: str = os.getenv("RUNWAY_MODEL", "gen4_turbo")
    runway_ratio: str = os.getenv("RUNWAY_RATIO", "1280:720")
    runway_duration: int = int(os.getenv("RUNWAY_DURATION", "5"))
    runway_poll_interval: float = float(
        os.getenv("RUNWAY_POLL_INTERVAL", "5")
    )
    runway_timeout: float = float(os.getenv("RUNWAY_TIMEOUT", "600"))
    runway_max_retries: int = int(os.getenv("RUNWAY_MAX_RETRIES", "3"))
    runway_image_model: str = os.getenv("RUNWAY_IMAGE_MODEL", "gen4_image")
    runway_reference_images: str = os.getenv("RUNWAY_REFERENCE_IMAGES", "")
    scene_min_duration: int = int(os.getenv("SCENE_MIN_DURATION", "5"))
    scene_max_duration: int = int(os.getenv("SCENE_MAX_DURATION", "8"))
    scene_generation_attempts: int = int(
        os.getenv("SCENE_GENERATION_ATTEMPTS", "3")
    )


settings = Settings()
settings.elevenlabs_voice_ids = {
    role: os.getenv(f"ELEVENLABS_{role.upper()}_VOICE_ID", "")
    for role in ("narrator", "leo", "scout", "mother", "father")
}
