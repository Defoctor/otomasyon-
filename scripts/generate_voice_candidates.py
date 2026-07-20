import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output" / "voice_candidates"
TEST_TEXT = (
    "Leo smiled as Scout bounced onto the branch. "
    "Together, they followed the sparkling trail toward a gentle new adventure."
)

ROLE_PROFILES = {
    "narrator": {
        "gender": {"female": 30},
        "age": {"young": 3, "middle_aged": 5},
        "accent": {"american": 3, "british": 3},
        "descriptive": {
            "professional": 12,
            "cute": 7,
            "upbeat": 6,
            "confident": 4,
        },
        "use_case": {
            "narrative_story": 16,
            "informative_educational": 8,
            "entertainment_tv": 7,
            "conversational": 6,
        },
        "name_terms": {
            "warm": 12,
            "story": 12,
            "natural": 8,
            "bright": 5,
            "reassuring": 5,
        },
    },
    "leo": {
        "gender": {"male": 30},
        "age": {"young": 20},
        "accent": {"american": 4, "british": 3, "australian": 2},
        "descriptive": {
            "chill": 10,
            "confident": 8,
            "hyped": 5,
            "casual": 4,
        },
        "use_case": {
            "conversational": 12,
            "characters_animation": 10,
            "social_media": 6,
        },
        "name_terms": {
            "relaxed": 10,
            "optimist": 10,
            "energetic": 8,
            "friendly": 7,
            "natural": 6,
        },
    },
    "scout": {
        "gender": {"male": 5, "female": 5, "neutral": 5},
        "age": {"young": 10, "middle_aged": 3},
        "accent": {"american": 4, "british": 2, "australian": 3},
        "descriptive": {
            "hyped": 12,
            "sassy": 11,
            "cute": 10,
            "confident": 7,
        },
        "use_case": {
            "characters_animation": 25,
            "social_media": 12,
            "conversational": 8,
        },
        "name_terms": {
            "trickster": 18,
            "quirky": 17,
            "energetic": 16,
            "playful": 15,
            "bright": 8,
        },
    },
    "mother": {
        "gender": {"female": 30},
        "age": {"middle_aged": 12, "young": 5},
        "accent": {"american": 4, "british": 3},
        "descriptive": {
            "professional": 7,
            "confident": 5,
            "cute": 4,
            "upbeat": 3,
        },
        "use_case": {
            "conversational": 12,
            "informative_educational": 8,
            "entertainment_tv": 6,
        },
        "name_terms": {
            "warm": 16,
            "reassuring": 15,
            "soft": 14,
            "calm": 12,
            "velvety": 9,
        },
    },
    "father": {
        "gender": {"male": 30},
        "age": {"middle_aged": 15},
        "accent": {"american": 4, "british": 3},
        "descriptive": {
            "classy": 8,
            "casual": 7,
            "formal": 2,
        },
        "use_case": {
            "conversational": 14,
            "narrative_story": 10,
            "informative_educational": 5,
        },
        "name_terms": {
            "trustworthy": 20,
            "comforting": 18,
            "warm": 16,
            "calm": 14,
            "relaxed": 10,
            "down-to-earth": 9,
        },
    },
}


def score_voice(voice, profile):
    labels = {
        str(key).lower(): str(value).lower()
        for key, value in (voice.labels or {}).items()
    }
    if labels.get("language") not in ("en", "english"):
        return None
    required_gender = max(profile["gender"], key=profile["gender"].get)
    if profile["gender"][required_gender] >= 30 and labels.get("gender") != required_gender:
        return None

    score = 0
    for field in ("gender", "age", "accent", "descriptive", "use_case"):
        score += profile[field].get(labels.get(field, ""), 0)
    name = (voice.name or "").lower()
    score += sum(
        points for term, points in profile["name_terms"].items() if term in name
    )
    return score, labels


def safe_filename(value):
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned[:70] or "voice"


def main():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(".env içinde ELEVENLABS_API_KEY bulunamadı.")

    client = ElevenLabs(api_key=api_key)
    voices = client.voices.get_all().voices
    results = []

    for role, profile in ROLE_PROFILES.items():
        ranked = []
        for voice in voices:
            scored = score_voice(voice, profile)
            if scored is not None:
                score, labels = scored
                ranked.append((score, voice, labels))
        ranked.sort(key=lambda item: (-item[0], item[1].name))
        selected = ranked[:3]
        if len(selected) < 3:
            raise RuntimeError(f"{role} için üç uygun hesap sesi bulunamadı.")

        role_dir = OUTPUT_ROOT / role
        role_dir.mkdir(parents=True, exist_ok=True)
        for score, voice, labels in selected:
            filename = (
                f"{safe_filename(voice.name)}_{voice.voice_id[:6]}.mp3"
            )
            output = role_dir / filename
            temporary = output.with_suffix(".mp3.tmp")
            audio = client.text_to_speech.convert(
                voice_id=voice.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                text=TEST_TEXT,
            )
            with temporary.open("wb") as file:
                for chunk in audio:
                    if chunk:
                        file.write(chunk)
            if temporary.stat().st_size == 0:
                temporary.unlink()
                raise RuntimeError(f"{role}/{voice.name} boş ses döndürdü.")
            temporary.replace(output)
            results.append(
                {
                    "role": role,
                    "voice_name": voice.name,
                    "voice_id": voice.voice_id,
                    "gender": labels.get("gender", ""),
                    "age": labels.get("age", ""),
                    "accent": labels.get("accent", ""),
                    "description": labels.get("descriptive", ""),
                    "test_file": str(output.resolve()),
                }
            )
            print(f"{role}: {voice.name} -> {output}")

    manifest = OUTPUT_ROOT / "voice_candidates.json"
    manifest.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"manifest: {manifest}")


if __name__ == "__main__":
    main()
