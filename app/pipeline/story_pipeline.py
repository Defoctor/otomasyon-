from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import secrets

from app.core.config import Settings
from app.core.exceptions import PersistenceError, StoryGenerationError
from app.database import Database, EpisodeRepository
from app.providers.base import StoryProvider
from app.providers.story import MockStoryProvider
from app.pipeline.episode_ids import next_episode_id
from app.schemas.story import Story, StoryCategory
from app.services.output_manager import OutputManager


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoryPipelineResult:
    episode_id: str
    episode_directory: Path
    story_path: Path
    character_bible_path: Path
    metadata_path: Path
    database_path: Path
    provider_name: str
    generation_seed: int


class StoryPipeline:
    def __init__(
        self,
        settings: Settings,
        provider: StoryProvider | None = None,
        database: Database | None = None,
    ):
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.repository = EpisodeRepository(self.database)
        self.output = OutputManager(settings.output_dir)
        self.provider = provider or self._provider_from_settings()

    def run(
        self,
        category: StoryCategory | None = None,
        duration_seconds: int | None = None,
        seed: int | None = None,
        idempotency_key: str | None = None,
    ) -> StoryPipelineResult:
        self.database.initialize()
        episode_id = next_episode_id(
            self.repository, self.settings.output_dir
        )
        selected_category = category or self._select_category(episode_id)
        target_duration = (
            duration_seconds
            if duration_seconds is not None
            else self.settings.default_duration_seconds
        )
        resolved_seed = seed if seed is not None else secrets.randbits(63)
        operation_key = idempotency_key or self._idempotency_key(
            episode_id, selected_category, target_duration, resolved_seed
        )
        LOGGER.info(
            "Generating %s with provider=%s category=%s duration=%s",
            episode_id,
            self.provider.provider_name,
            selected_category.value,
            target_duration,
        )
        try:
            story = self.provider.generate(
                episode_id=episode_id,
                category=selected_category,
                duration_seconds=target_duration,
                seed=resolved_seed,
            )
        except Exception as exc:
            LOGGER.exception("Story generation failed for %s", episode_id)
            raise StoryGenerationError(
                f"Story generation failed for {episode_id}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        try:
            files = self.output.write_story_files(
                story, self.provider.provider_name, resolved_seed
            )
            saved_episode_id = self.repository.save_story(
                story=story,
                story_json_path=str(files["story"]),
                provider_name=self.provider.provider_name,
                idempotency_key=operation_key,
            )
        except Exception as exc:
            LOGGER.exception("Saving episode failed for %s", episode_id)
            raise PersistenceError(
                f"Could not save {episode_id}: {type(exc).__name__}: {exc}"
            ) from exc

        LOGGER.info("Episode %s saved successfully", saved_episode_id)
        return StoryPipelineResult(
            episode_id=saved_episode_id,
            episode_directory=files["story"].parent,
            story_path=files["story"],
            character_bible_path=files["character_bible"],
            metadata_path=files["metadata"],
            database_path=self.database.path,
            provider_name=self.provider.provider_name,
            generation_seed=resolved_seed,
        )

    def _provider_from_settings(self) -> StoryProvider:
        if self.settings.story_provider == "mock":
            return MockStoryProvider()
        raise StoryGenerationError(
            f"Unsupported STORY_PROVIDER={self.settings.story_provider!r}. "
            "AŞAMA 1 supports only 'mock'."
        )

    def _select_category(self, episode_id: str) -> StoryCategory:
        configured = self.settings.default_story_category
        if configured != "auto":
            try:
                return StoryCategory(configured)
            except ValueError as exc:
                allowed = ", ".join(item.value for item in StoryCategory)
                raise StoryGenerationError(
                    f"Unknown story category {configured!r}. Allowed: {allowed}."
                ) from exc
        categories = list(StoryCategory)
        number = int(episode_id.rsplit("_", 1)[1])
        return categories[(number - 1) % len(categories)]

    @staticmethod
    def _idempotency_key(
        episode_id: str,
        category: StoryCategory,
        duration_seconds: int,
        seed: int | None,
    ) -> str:
        value = f"{episode_id}:{category.value}:{duration_seconds}:{seed}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
