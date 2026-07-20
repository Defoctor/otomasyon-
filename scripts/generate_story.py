import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.pipeline import StoryPipeline  # noqa: E402
from app.schemas.story import StoryCategory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one validated six-scene kids Shorts story in demo mode."
        )
    )
    parser.add_argument(
        "--category",
        choices=[item.value for item in StoryCategory],
        help="Optional story category; defaults to automatic rotation.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Target duration in seconds (25-35).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional deterministic mock generation seed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level, ROOT / "logs")
    category = StoryCategory(args.category) if args.category else None
    result = StoryPipeline(settings).run(
        category=category,
        duration_seconds=args.duration,
        seed=args.seed,
    )
    print(f"STATUS=completed")
    print(f"MODE=demo")
    print(f"PROVIDER={result.provider_name}")
    print(f"EPISODE_ID={result.episode_id}")
    print(f"OUTPUT_DIR={result.episode_directory}")
    print(f"STORY_JSON={result.story_path}")
    print(f"CHARACTER_BIBLE_JSON={result.character_bible_path}")
    print(f"METADATA_JSON={result.metadata_path}")
    print(f"DATABASE={result.database_path}")
    print("MANUAL_APPROVAL_REQUIRED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
