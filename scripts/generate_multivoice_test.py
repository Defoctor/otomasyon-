import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import settings  # noqa: E402
from src.pipeline import get_voice_provider  # noqa: E402


def main():
    root = Path("output/multivoice_test_story").resolve()
    segments = [
        {
            "speaker": "narrator",
            "text": (
                "On a bright Saturday morning, a new adventure began near the forest."
            ),
        },
        {
            "speaker": "leo",
            "text": "Scout, look! A trail of golden leaves leads to our treehouse!",
        },
        {
            "speaker": "scout",
            "text": (
                "Then let us hurry, Leo! I bet there is a wonderfully nutty "
                "mystery waiting!"
            ),
        },
        {
            "speaker": "leo",
            "text": (
                "You were right, Scout! The silver key fits the tiny door "
                "behind the old tree."
            ),
        },
        {
            "speaker": "mother",
            "text": "Stay together, be kind, and come home before supper.",
        },
        {
            "speaker": "father",
            "text": "And remember, the best explorers always help one another.",
        },
    ]

    provider = get_voice_provider()
    output = provider.synthesize_dialogue(
        segments,
        root / "test_story.mp3",
        root / "segments",
    )

    records = []
    for index, segment in enumerate(segments, start=1):
        path = root / "segments" / f"{index:03d}_{segment['speaker']}.mp3"
        records.append(
            {
                "speaker": segment["speaker"],
                "voice_id": settings.elevenlabs_voice_ids[segment["speaker"]],
                "text": segment["text"],
                "file": str(path),
                "bytes": path.stat().st_size,
            }
        )
    (root / "verification.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"OUTPUT={output}")
    print(f"BYTES={output.stat().st_size}")
    print(f"SEGMENTS={len(records)}")
    for record in records:
        print(
            f"{record['speaker']}|{record['voice_id'][:6]}|"
            f"{record['bytes']}|{record['file']}"
        )


if __name__ == "__main__":
    main()
