import json
from pathlib import Path

from app.web.repository import WebRepository
from app.web.schemas import EpisodeDetailResponse
from app.web.security import safe_episode_directory


class EpisodeWebService:
    def __init__(self, repository: WebRepository, output_root: Path):
        self.repository = repository
        self.output_root = output_root

    def detail(self, episode_id: str) -> EpisodeDetailResponse:
        summaries = self.repository.list_episodes()
        summary = next(
            (item for item in summaries if item.episode_id == episode_id),
            None,
        )
        if summary is None:
            raise KeyError(f"Episode not found: {episode_id}")
        directory = safe_episode_directory(self.output_root, episode_id)
        story = _read_json(directory / "story.json")
        bible = _read_json(directory / "character_bible.json")
        metadata = _read_json(directory / "metadata.json")
        quality_path = directory / "quality_report.json"
        quality = _read_json(quality_path) if quality_path.is_file() else None
        media = {
            "images": _relative_files(directory, "images", "*.png"),
            "clips": _relative_files(directory, "clips", "*.mp4"),
            "audio": _relative_files(directory, "audio", "*"),
            "subtitles": _relative_files(directory, "subtitles", "*"),
            "final_video": (
                "final_short.mp4"
                if (directory / "final_short.mp4").is_file()
                else None
            ),
        }
        return EpisodeDetailResponse(
            episode=summary,
            story=story,
            character_bible=bible,
            metadata=metadata,
            quality_report=quality,
            assets=self.repository.assets(episode_id),
            media=media,
        )


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _relative_files(directory: Path, folder: str, pattern: str) -> list[str]:
    root = directory / folder
    if not root.is_dir():
        return []
    return [
        path.relative_to(directory).as_posix()
        for path in sorted(root.glob(pattern))
        if path.is_file()
    ]
