from pathlib import Path
import json
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline


STATUS = ROOT / "output" / "first_episode_status.json"


def main() -> int:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run_pipeline(
            {
                "id": "leo-meets-scout",
                "title": "Leo Finds an Injured Little Squirrel Named Scout",
                "angle": (
                    "In the forest, Leo discovers Scout with a small injured "
                    "paw. Scout is frightened of Leo at first. Leo stays calm, "
                    "gently helps him, and earns his trust. Their very first "
                    "friendship begins. Keep the injury mild and non-graphic."
                ),
                "audience": "English-speaking children ages 3 to 10",
            },
            target_minutes=2,
        )
        payload = {
            "status": "completed",
            "project_dir": str(result["project_dir"].resolve()),
            "video_path": (
                str(result["video_path"].resolve())
                if result["video_path"]
                else None
            ),
            "scene_count": len(result["content"].scenes),
            "scenes": [
                {
                    "number": scene.number,
                    "duration": scene.duration_seconds,
                    "narration": scene.narration,
                }
                for scene in result["content"].scenes
            ],
        }
        STATUS.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        STATUS.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
