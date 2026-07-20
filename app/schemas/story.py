from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StoryCategory(str, Enum):
    ANIMAL_RESCUE = "animal_rescue"
    LOST_BABY_ANIMAL = "lost_baby_animal"
    UNEXPECTED_FRIENDSHIP = "unexpected_friendship"
    SMALL_MEETS_BIG = "small_meets_big"
    FUNNY_FAILURE = "funny_failure_and_fix"
    MYSTERY_OBJECT = "mystery_box_or_object"
    COLOR_TRANSFORMATION = "color_or_shape_transformation"
    EMOTIONAL_HAPPY_ENDING = "emotional_to_happy"
    COURAGE_AND_TEAMWORK = "courage_and_teamwork"
    MISUNDERSTOOD_CREATURE = "misunderstood_cute_creature"


class MainCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_id: str = Field(min_length=3, pattern=r"^[a-z0-9_]+$")
    species: str = Field(min_length=2)
    age_style: str = Field(min_length=2)
    body_shape: str = Field(min_length=2)
    fur_or_skin_color: str = Field(min_length=2)
    eye_color: str = Field(min_length=2)
    clothes: str = Field(min_length=2)
    accessories: str = Field(min_length=2)
    personality: str = Field(min_length=2)
    distinguishing_features: str = Field(min_length=2)
    visual_style: str = Field(min_length=2)
    negative_prompt: str = Field(min_length=2)

    def prompt_signature(self) -> str:
        return (
            f"CHARACTER LOCK: {self.species}; {self.age_style}; "
            f"{self.body_shape}; {self.fur_or_skin_color}; "
            f"{self.eye_color}; wearing {self.clothes}; "
            f"accessories: {self.accessories}; distinguishing features: "
            f"{self.distinguishing_features}; personality: {self.personality}; "
            f"style: {self.visual_style}."
        )


class CharacterBible(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_character: MainCharacter


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_number: int = Field(ge=1, le=6)
    duration_seconds: int = Field(ge=4, le=6)
    narration: str = Field(min_length=8, max_length=240)
    visual_prompt: str = Field(min_length=30)
    motion_prompt: str = Field(min_length=8)
    sound_effects: list[str] = Field(default_factory=list, max_length=4)
    emotion: str = Field(min_length=2)

    @field_validator("narration")
    @classmethod
    def narration_must_not_contain_dialogue(cls, value: str) -> str:
        if '"' in value or "“" in value or "”" in value:
            raise ValueError("Narration must not contain character dialogue.")
        return value.strip()


class Story(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(pattern=r"^episode_\d{4,}$")
    language: str = Field(pattern=r"^en$")
    duration_target_seconds: int = Field(ge=25, le=35)
    story_category: StoryCategory
    title: str = Field(min_length=5, max_length=100)
    hook: str = Field(min_length=8, max_length=180)
    hook_type: str = Field(min_length=2)
    character_bible: CharacterBible
    scenes: list[Scene] = Field(min_length=6, max_length=6)
    music_mood: str = Field(min_length=2)
    ending_type: str = Field(min_length=2)
    loop_hint: str = Field(min_length=8)
    content_summary: str = Field(min_length=8, max_length=300)
    tags: list[str] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def validate_story_structure(self) -> "Story":
        expected = list(range(1, 7))
        actual = [scene.scene_number for scene in self.scenes]
        if actual != expected:
            raise ValueError("Scenes must be numbered consecutively from 1 to 6.")

        total_duration = sum(scene.duration_seconds for scene in self.scenes)
        if not 25 <= total_duration <= 35:
            raise ValueError(
                "Total scene duration must be between 25 and 35 seconds."
            )
        if total_duration != self.duration_target_seconds:
            raise ValueError(
                "duration_target_seconds must equal total scene duration."
            )

        signature = self.character_bible.main_character.prompt_signature()
        missing = [
            scene.scene_number
            for scene in self.scenes
            if signature not in scene.visual_prompt
        ]
        if missing:
            raise ValueError(
                f"Character lock is missing from scene prompts: {missing}."
            )
        return self
