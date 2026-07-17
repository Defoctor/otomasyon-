from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    content_provider: str = os.getenv("CONTENT_PROVIDER", "fake")
    voice_provider: str = os.getenv("VOICE_PROVIDER", "fake")
    media_provider: str = os.getenv("MEDIA_PROVIDER", "fake")
    youtube_upload_enabled: bool = (
        os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true"
    )
    projects_dir: Path = ROOT / "data" / "projects"
    topics_file: Path = ROOT / "data" / "topics.json"


settings = Settings()
