import json
from pathlib import Path
from typing import Any

from app.schemas.story import Story


class OutputManager:
    def __init__(self, root: Path):
        self.root = root

    def episode_directory(self, episode_id: str) -> Path:
        return self.root / episode_id

    def write_story_files(
        self,
        story: Story,
        provider_name: str,
        generation_seed: int | None = None,
    ) -> dict[str, Path]:
        directory = self.episode_directory(story.episode_id)
        directory.mkdir(parents=True, exist_ok=False)
        files = {
            "story": directory / "story.json",
            "character_bible": directory / "character_bible.json",
            "metadata": directory / "metadata.json",
        }
        self._write_json(files["story"], story.model_dump(mode="json"))
        self._write_json(
            files["character_bible"],
            story.character_bible.model_dump(mode="json"),
        )
        self._write_json(
            files["metadata"],
            {
                "episode_id": story.episode_id,
                "story_category": story.story_category.value,
                "main_character_type": (
                    story.character_bible.main_character.species
                ),
                "character_id": (
                    story.character_bible.main_character.character_id
                ),
                "hook_type": story.hook_type,
                "ending_type": story.ending_type,
                "duration_seconds": story.duration_target_seconds,
                "providers_used": {"story": provider_name},
                "generation_cost_estimate_usd": 0.0,
                "approval_status": "pending",
                "upload_status": "not_ready",
                "requires_manual_approval": True,
                "demo_mode": provider_name == "mock",
                "generation_seed": generation_seed,
            },
        )
        return files

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
