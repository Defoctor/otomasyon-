from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.story import StoryCategory


class WebJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class GenerateEpisodeRequest(BaseModel):
    create_story: bool = True
    episode_id: str | None = None
    automatic_category: bool = True
    category: StoryCategory | None = None
    duration_seconds: int = Field(default=30, ge=25, le=35)
    seed: int | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> "GenerateEpisodeRequest":
        if self.create_story and self.episode_id:
            raise ValueError(
                "episode_id cannot be used when create_story is true."
            )
        if not self.create_story and not self.episode_id:
            raise ValueError(
                "episode_id is required when create_story is false."
            )
        if not self.automatic_category and self.category is None:
            raise ValueError("A manual category must be selected.")
        return self


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class DeleteMediaRequest(BaseModel):
    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def confirmation_must_match(cls, value: str) -> str:
        if value != "DELETE_MEDIA":
            raise ValueError("confirmation must equal DELETE_MEDIA.")
        return value


class JobResponse(BaseModel):
    job_id: str
    episode_id: str | None
    job_type: str
    scene_number: int | None
    status: str
    current_stage: str
    progress_percent: int
    error_message: str | None
    retry_count: int
    created_at: str
    updated_at: str


class ActionResponse(BaseModel):
    episode_id: str
    approval_status: str
    upload_status: str
    message: str


class SystemStatusResponse(BaseModel):
    status: str
    ffmpeg: bool
    ffprobe: bool
    providers: dict[str, str]
    totals: dict[str, int]


class EpisodeSummaryResponse(BaseModel):
    episode_id: str
    title: str
    category: str
    main_character: str
    duration: int
    creation_date: str
    generation_status: str
    approval_status: str
    upload_status: str
    providers: dict[str, str]
    final_video_exists: bool
    quality_status: str


class EpisodeDetailResponse(BaseModel):
    episode: EpisodeSummaryResponse
    story: dict
    character_bible: dict
    metadata: dict
    quality_report: dict | None
    assets: list[dict]
    media: dict[str, list[str] | str | None]
