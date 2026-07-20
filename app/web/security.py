from pathlib import Path
import re

from fastapi import HTTPException


EPISODE_ID_PATTERN = re.compile(r"^episode_[0-9]{4,}$")


def validate_episode_id(value: str) -> str:
    if not EPISODE_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=422, detail="Invalid episode ID.")
    return value


def validate_scene_number(value: int) -> int:
    if value not in range(1, 7):
        raise HTTPException(
            status_code=422, detail="Scene number must be between 1 and 6."
        )
    return value


def safe_episode_directory(output_root: Path, episode_id: str) -> Path:
    validate_episode_id(episode_id)
    root = output_root.resolve()
    candidate = (root / episode_id).resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=403, detail="Unsafe episode path.")
    return candidate


def safe_media_path(
    output_root: Path, episode_id: str, relative_path: str
) -> Path:
    episode = safe_episode_directory(output_root, episode_id)
    if not relative_path or "\x00" in relative_path:
        raise HTTPException(status_code=422, detail="Invalid media path.")
    supplied = Path(relative_path.replace("\\", "/"))
    if supplied.is_absolute() or ".." in supplied.parts:
        raise HTTPException(status_code=403, detail="Path traversal blocked.")
    candidate = (episode / supplied).resolve()
    if not candidate.is_relative_to(episode):
        raise HTTPException(status_code=403, detail="Path traversal blocked.")
    return candidate


def redact_secrets(text: str) -> str:
    patterns = [
        r"(?i)(OPENAI_API_KEY\s*[=:]\s*)\S+",
        r"(?i)(ELEVENLABS_API_KEY\s*[=:]\s*)\S+",
        r"(?i)(RUNWAY_API_KEY\s*[=:]\s*)\S+",
        r"(?i)(api[_-]?key\s*[=:]\s*)\S+",
        r"(?i)(authorization\s*[=:]\s*bearer\s+)\S+",
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, r"\1***REDACTED***", result)
    return result
