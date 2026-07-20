from pathlib import Path
import re

from app.database.repositories import EpisodeRepository


EPISODE_PATTERN = re.compile(r"^episode_(\d{4,})$")


def next_episode_id(
    repository: EpisodeRepository, output_root: Path
) -> str:
    database_id = repository.next_episode_id()
    maximum = int(database_id.rsplit("_", 1)[1]) - 1
    if output_root.exists():
        for path in output_root.iterdir():
            if not path.is_dir():
                continue
            match = EPISODE_PATTERN.fullmatch(path.name)
            if match:
                maximum = max(maximum, int(match.group(1)))
    return f"episode_{maximum + 1:04d}"
