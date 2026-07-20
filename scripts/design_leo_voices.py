import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "voice_candidates" / "leo_designed"
DESCRIPTION = (
    "Young boy character, approximately 8 to 10 years old, noticeably youthful "
    "and slightly high-pitched, warm, innocent, curious and energetic. Clear "
    "American English, natural childlike delivery, suitable for an animated "
    "children's adventure series. Expressive but not squeaky, not babyish, and "
    "not an adult imitating a child."
)
TEST_SENTENCE = (
    "Scout, wait for me! I think I found something amazing behind the old tree!"
)
PREVIEW_TEXT = f"{TEST_SENTENCE} {TEST_SENTENCE}"


def main():
    load_dotenv(ROOT / ".env", override=True)
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(".env içinde ELEVENLABS_API_KEY bulunamadı.")

    client = ElevenLabs(api_key=api_key)
    response = client.text_to_voice.design(
        model_id="eleven_multilingual_ttv_v2",
        voice_description=DESCRIPTION,
        text=PREVIEW_TEXT,
        output_format="mp3_44100_128",
        guidance_scale=5,
        quality=0.9,
    )
    if len(response.previews) != 3:
        raise RuntimeError(
            f"Voice Design API 3 yerine {len(response.previews)} ön izleme döndürdü."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for index, preview in enumerate(response.previews, start=1):
        candidate_name = f"Leo Designed Candidate {index}"
        generated_id = preview.generated_voice_id
        output = OUTPUT_DIR / f"leo_candidate_{index}_{generated_id[:6]}.mp3"
        temporary = output.with_suffix(".mp3.tmp")
        temporary.write_bytes(base64.b64decode(preview.audio_base_64))
        if temporary.stat().st_size == 0:
            temporary.unlink()
            raise RuntimeError(f"{candidate_name} boş ses döndürdü.")
        temporary.replace(output)
        records.append(
            {
                "name": candidate_name,
                "generated_voice_id": generated_id,
                "file": str(output.resolve()),
                "bytes": output.stat().st_size,
                "test_sentence": TEST_SENTENCE,
                "preview_text_repetitions": 2,
            }
        )
        print(
            f"{candidate_name}|{generated_id}|{output.resolve()}|"
            f"{output.stat().st_size}"
        )

    manifest = OUTPUT_DIR / "leo_designed_candidates.json"
    manifest.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"MANIFEST={manifest.resolve()}")


if __name__ == "__main__":
    main()
