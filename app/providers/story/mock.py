import hashlib
import random

from app.providers.base import StoryProvider
from app.schemas.story import (
    CharacterBible,
    MainCharacter,
    Scene,
    Story,
    StoryCategory,
)


CHARACTERS = [
    ("red panda", "warm russet fur with cream cheeks", "large teal eyes", "a sunflower-yellow raincoat", "a leaf-shaped green satchel", "a striped fluffy tail", "small round body", "kind, observant, and brave"),
    ("otter", "cocoa-brown fur with a pale belly", "large amber eyes", "a coral knitted scarf", "a blue shell bracelet", "three pale whisker dots", "small smooth body", "playful, caring, and persistent"),
    ("rabbit", "lavender-gray fur with white paws", "large moss-green eyes", "mint-green overalls", "a star-shaped wooden button", "one ear folded at the tip", "tiny pear-shaped body", "curious, gentle, and inventive"),
    ("fox", "soft orange fur with a white chest", "large emerald eyes", "a sky-blue scarf", "a wooden acorn pin", "a bright white tail tip", "small agile body", "warm, clever, and helpful"),
    ("hedgehog", "caramel spines and a cream face", "round hazel eyes", "a berry-purple vest", "a tiny canvas pouch", "three heart-shaped forehead marks", "small oval body", "patient, cheerful, and resourceful"),
    ("koala", "silver-gray fur with fluffy ears", "large violet eyes", "a peach neckerchief", "a eucalyptus badge", "a heart-shaped nose", "small cuddly body", "calm, thoughtful, and loyal"),
    ("squirrel", "cinnamon fur with a cream belly", "bright blue eyes", "a green explorer jacket", "a tiny compass charm", "an extra-curly tail", "small springy body", "quick, friendly, and optimistic"),
    ("penguin", "midnight-blue feathers with a white belly", "large brown eyes", "a tangerine bow tie", "a snowflake satchel", "one freckle beside the beak", "small rounded body", "polite, determined, and caring"),
    ("mouse", "honey-beige fur with pink ears", "large gray-blue eyes", "a red pocket vest", "a button-sized backpack", "a crescent mark on one ear", "tiny round body", "bold, imaginative, and generous"),
    ("turtle", "mint-green skin and a jade shell", "large golden eyes", "a soft yellow cap", "a woven reed bracelet", "a spiral shell marking", "small sturdy body", "steady, wise, and encouraging"),
]

OPENINGS = [
    "A glowing paper star tumbled from the sky beside {hero}.",
    "At sunrise, {hero} discovered tiny sparkling footprints.",
    "A rainbow-colored breeze delivered a folded leaf map to {hero}.",
    "Just before the rain, a silver humming sound surprised {hero}.",
    "A bouncing blue light led {hero} beyond the garden gate.",
    "One quiet morning, {hero} found a warm pebble pulsing like a heartbeat.",
    "A trail of golden bubbles appeared in front of {hero}.",
    "The smallest cloud lowered a mysterious ribbon toward {hero}.",
    "A shy lantern blinked three times from behind a tree near {hero}.",
    "A spinning seed landed on {hero}'s nose and pointed toward adventure.",
]

PROBLEMS = [
    "a baby duck could not cross a wide puddle",
    "a tiny bird had lost the nest it called home",
    "a frightened firefly could no longer make its light glow",
    "a little frog was stranded beyond a maze of fallen leaves",
    "a cloud had misplaced the silver bell that guided it home",
    "a young mole could not find the entrance to a family picnic",
    "a sleepy snail's treasure cart was stuck in soft mud",
    "a small fish was separated from its pond by a shallow stream",
    "a bashful caterpillar had lost a colorful keepsake",
    "a baby owl was confused by echoes in the moonlit garden",
]

SOLUTIONS = [
    "built a gentle bridge from broad leaves",
    "followed the clues and arranged bright stones into an arrow",
    "shared a glowing keepsake until courage returned",
    "made a safe path by rolling smooth twigs into place",
    "asked nearby animals to form a cheerful helping line",
    "used reflected sunlight to reveal the hidden route",
    "turned fallen petals into tiny guiding flags",
    "floated a sturdy bark raft across the shallow water",
    "stacked soft moss into safe little stepping stones",
    "matched each echo with a friendly forest sound",
]

OBJECTS = ["silver bell", "leaf map", "paper star", "striped ribbon", "warm pebble", "tiny lantern", "blue feather", "golden button", "glass acorn", "rainbow seed"]
LOCATIONS = ["sunlit forest clearing", "wildflower meadow", "willow pond", "mossy garden", "cloudberry hill", "quiet bamboo grove", "seaside dune", "autumn orchard", "moonlit fern path", "crystal creek"]
OUTCOMES = [
    "The reunion filled the air with warm golden sparkles.",
    "Everyone laughed as the helpful object gave one joyful bounce.",
    "A soft rainbow appeared, and every worried face became a smile.",
    "The new friends celebrated with a tiny dance under the leaves.",
    "The rescued little one returned with a handmade thank-you badge.",
    "The whole clearing glowed gently as the friends hugged.",
    "A chorus of birds marked the happy ending with a bright melody.",
    "The final puddle ripple formed a heart before fading away.",
    "The smallest helper received the biggest cheerful wave.",
    "The mysterious object floated home, leaving a trail of stars.",
]

CATEGORY_BEATS = {
    StoryCategory.ANIMAL_RESCUE: ("rescue mission", "reach the stranded friend", "safe rescue"),
    StoryCategory.LOST_BABY_ANIMAL: ("search for home", "follow signs left by the family", "family reunion"),
    StoryCategory.UNEXPECTED_FRIENDSHIP: ("unlikely meeting", "learn to cooperate despite their differences", "new friendship"),
    StoryCategory.SMALL_MEETS_BIG: ("surprising size difference", "combine a tiny idea with great strength", "shared respect"),
    StoryCategory.FUNNY_FAILURE: ("playful mistake", "try a smarter and funnier second plan", "cheerful success"),
    StoryCategory.MYSTERY_OBJECT: ("mysterious discovery", "solve the object's gentle clues", "delightful reveal"),
    StoryCategory.COLOR_TRANSFORMATION: ("magical change", "restore the missing colors together", "colorful celebration"),
    StoryCategory.EMOTIONAL_HAPPY_ENDING: ("lonely beginning", "offer patient kindness and hope", "heartwarming reunion"),
    StoryCategory.COURAGE_AND_TEAMWORK: ("team challenge", "give every helper one important task", "brave team victory"),
    StoryCategory.MISUNDERSTOOD_CREATURE: ("mistaken first impression", "discover the creature's kind intention", "welcoming friendship"),
}


class MockStoryProvider(StoryProvider):
    """Offline, category-aware and seed-deterministic story provider."""

    provider_name = "mock"

    def generate(self, episode_id: str, category: StoryCategory, duration_seconds: int, seed: int | None = None) -> Story:
        resolved_seed = seed if seed is not None else _stable_seed(episode_id, category)
        rng = random.Random(resolved_seed)
        profile = rng.choice(CHARACTERS)
        opening = rng.choice(OPENINGS)
        problem = rng.choice(PROBLEMS)
        solution = rng.choice(SOLUTIONS)
        object_name = rng.choice(OBJECTS)
        location = rng.choice(LOCATIONS)
        outcome = rng.choice(OUTCOMES)
        beat, action, ending = CATEGORY_BEATS[category]
        species = profile[0]
        episode_number = episode_id.rsplit("_", 1)[-1]
        character = MainCharacter(
            character_id=f"{species.replace(' ', '_')}_{episode_number}_{rng.randint(100, 999)}",
            species=species, age_style="young storybook animal", body_shape=profile[6],
            fur_or_skin_color=profile[1], eye_color=profile[2], clothes=profile[3],
            accessories=profile[4], personality=profile[7], distinguishing_features=profile[5],
            visual_style="high-quality colorful 3D children's animation, soft cinematic lighting, rounded shapes, vertical 9:16 composition",
            negative_prompt="violence, fear, danger, adult content, copyrighted character, brand logo, text, watermark, extra limbs, inconsistent colors",
        )
        hero = f"a tiny {species}"
        hook = opening.format(hero=hero)
        narrations = [
            hook,
            f"In the {location}, the {species} learned that {problem}.",
            f"What began as a {beat} grew harder when the {object_name} slipped out of reach.",
            f"The thoughtful {species} decided to {action} and {solution}.",
            f"The plan worked, bringing a {ending} for everyone in the {location}.",
            outcome + f" The {object_name} softly echoed the adventure's beginning.",
        ]
        settings = [
            f"A striking opening in a {location}, featuring a large {object_name} and a surprised {species}.",
            f"The {location} reveals the safe problem: {problem}.",
            f"The challenge grows around the {object_name}, with clear child-safe visual stakes.",
            f"The character performs the solution: {solution}.",
            f"Warm celebration showing the category result: {ending}.",
            f"A peaceful loop composition in the {location}, with the {object_name} returning to its opening position.",
        ]
        motions = ["Quick gentle push-in with a surprised reaction.", "Slow side tracking shot toward the friend in need.", "Camera tilts toward the growing challenge.", "Smooth close-up follows the careful solution.", "Small joyful orbit as warm particles drift.", "Slow pull-back that matches the opening frame."]
        emotions = ["wonder", "concern", "hopeful tension", "determination", "joy", "warm satisfaction"]
        durations = _scene_durations(duration_seconds)
        lock = character.prompt_signature()
        scenes = [Scene(scene_number=i, duration_seconds=durations[i-1], narration=narrations[i-1], visual_prompt=f"{lock} {settings[i-1]} Keep all character details unchanged. Negative prompt: {character.negative_prompt}.", motion_prompt=motions[i-1], sound_effects=["gentle ambience", object_name], emotion=emotions[i-1]) for i in range(1, 7)]
        title = f"The {species.title()} and the {object_name.title()}: {ending.title()}"
        return Story(
            episode_id=episode_id, language="en", duration_target_seconds=sum(durations),
            story_category=category, title=title, hook=hook,
            hook_type=beat.replace(" ", "_"), character_bible=CharacterBible(main_character=character),
            scenes=scenes, music_mood=f"curious and gentle, becoming uplifting after the {ending}",
            ending_type=ending.replace(" ", "_"),
            loop_hint=f"The final {object_name} movement softly matches the opening.",
            content_summary=f"In a {location}, a kind {species} helps when {problem} and creates a {ending}.",
            tags=["kids story", category.value.replace("_", " "), species, object_name, "YouTube Shorts"],
        )


def _stable_seed(episode_id: str, category: StoryCategory) -> int:
    digest = hashlib.sha256(f"{episode_id}:{category.value}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _scene_durations(total: int) -> list[int]:
    if not 25 <= total <= 35:
        raise ValueError("Duration must be between 25 and 35 seconds.")
    durations = [4] * 6
    remaining = total - sum(durations)
    index = 0
    while remaining:
        if durations[index] < 6:
            durations[index] += 1
            remaining -= 1
        index = (index + 1) % 6
    return durations
