import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.database import Database, EpisodeRepository  # noqa: E402
from app.pipeline import DemoVideoPipeline, StoryPipeline  # noqa: E402
from app.schemas.story import StoryCategory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a completely local demo YouTube Shorts MP4."
    )
    parser.add_argument("--episode", help="Existing episode ID to render.")
    parser.add_argument(
        "--create-story",
        action="store_true",
        help="Run AŞAMA 1 before rendering AŞAMA 2.",
    )
    parser.add_argument(
        "--seed", type=int, help="Deterministic mock story seed."
    )
    parser.add_argument(
        "--category",
        choices=[item.value for item in StoryCategory],
        help="Story category used with --create-story.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Story duration from 25 through 35 seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level, ROOT / "logs")
    wants_story = (
        args.create_story
        or args.seed is not None
        or args.category is not None
        or args.duration is not None
    )
    if args.episode and wants_story:
        raise ValueError(
            "--episode cannot be combined with story creation options."
        )

    if wants_story:
        story_result = StoryPipeline(settings).run(
            category=(
                StoryCategory(args.category) if args.category else None
            ),
            duration_seconds=args.duration,
            seed=args.seed,
        )
        episode_id = story_result.episode_id
    elif args.episode:
        episode_id = args.episode
    else:
        database = Database(settings.database_path)
        database.initialize()
        episode_id = EpisodeRepository(database).latest_episode_id()
        if episode_id is None:
            raise RuntimeError(
                "No episode exists. Use --create-story to create one."
            )

    result = DemoVideoPipeline(settings).run(episode_id)
    print("STATUS=completed")
    print("MODE=demo")
    print(f"EPISODE_ID={result.episode_id}")
    print(f"IMAGES_DIR={result.images_directory}")
    print(f"CLIPS_DIR={result.clips_directory}")
    print(f"NARRATION={result.narration_path}")
    print(f"TTS_PROVIDER_USED={result.tts_provider_used}")
    print(f"MUSIC={result.music_path}")
    print(f"SOUND_EFFECTS={result.effects_path}")
    print(f"FINAL_MIX={result.final_mix_path}")
    print(f"SUBTITLES={result.subtitles_directory}")
    print(f"FINAL_VIDEO={result.final_video_path}")
    print(f"QUALITY_REPORT={result.quality_report_path}")
    print(f"DATABASE={result.database_path}")
    print(f"RENDER_SECONDS={result.render_seconds:.2f}")
    print("MANUAL_APPROVAL_REQUIRED=true")
    print("UPLOAD_STATUS=not_ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
