from abc import ABC, abstractmethod
import json
import os
from typing import Any

from src.memory import MemoryStore
from src.models import ContentPackage, Scene


class ContentProvider(ABC):
    @abstractmethod
    def generate(self, topic: dict, target_minutes: int) -> ContentPackage:
        raise NotImplementedError


class FakeContentProvider(ContentProvider):
    """API anahtarı kullanmadan deterministik test içeriği üretir."""

    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store

    def generate(self, topic: dict, target_minutes: int) -> ContentPackage:
        self.memory_store.load_all()
        title = f"{topic['title']}: Bildiğimizi Sandığımız 5 Gerçek"
        intro = (
            f"Bugün {topic['title'].lower()} konusuna bakıyoruz. "
            "Efsanelerle doğrulanabilir bilgileri ayırıp en ilginç ayrıntıları inceleyeceğiz."
        )
        facts = [
            "İlk ipucu, eski haritalar ile modern araştırmaların aynı noktada buluşmasıdır.",
            "İkinci ayrıntı, dönemin insanlarının sanılandan daha gelişmiş yöntemler kullanmasıdır.",
            "Üçüncü bulgu, popüler anlatıların her zaman arkeolojik kanıtlarla uyuşmadığını gösterir.",
            "Dördüncü nokta, coğrafyanın insanların kararlarını nasıl değiştirdiğini açıklar.",
            "Son ayrıntı ise yeni araştırmaların eski kabulleri hâlâ değiştirebildiğini hatırlatır.",
        ]
        outro = (
            "Bu hikâyenin en güçlü tarafı, kesin cevaplardan çok yeni sorular doğurması. "
            "Benzer kısa belgeseller için kanalı takip edebilirsiniz."
        )
        extra_scene = (
            "Leo ve Scout, merak ve ekip Ã§alÄ±ÅŸmasÄ±yla ipuÃ§larÄ± arasÄ±nda "
            "yeni bir baÄŸlantÄ± kurar."
        )
        paragraphs = [intro] + facts + [extra_scene, outro]
        # Demo kısa tutulur; gerçek sağlayıcı hedef süreye göre metni genişletir.
        scene_duration = max(5, round(target_minutes * 60 / len(paragraphs)))
        scenes = [
            Scene(
                number=index,
                narration=text,
                visual_prompt=f"Belgesel tarzı, sinematik, telifsiz özgün sahne: {text}",
                duration_seconds=scene_duration,
                speech=[{"speaker": "narrator", "text": text}],
            )
            for index, text in enumerate(paragraphs, start=1)
        ]
        content = ContentPackage(
            topic=topic["title"],
            title=title,
            description=(
                f"{topic['title']} hakkında kaynak kontrolüne uygun, kısa belgesel anlatımı.\n\n"
                "Not: Bu sürüm test verisi üretir; yayınlamadan önce bilgi ve kaynak kontrolü yapın."
            ),
            tags=["tarih", "belgesel", "ilginç bilgiler", "gizem", "kısa belgesel"],
            script="\n\n".join(paragraphs),
            scenes=scenes,
        )
        self.memory_store.record_story(content.title, content.topic)
        return content


class OpenAIContentProvider(ContentProvider):
    """OpenAI Responses API ile çocuklara uygun İngilizce hikâye üretir."""

    def __init__(
        self, model: str, memory_store: MemoryStore, client: Any | None = None
    ):
        self.model = model
        self.memory_store = memory_store
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "CONTENT_PROVIDER=openai için .env dosyasında OPENAI_API_KEY tanımlanmalıdır."
            )

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        return self._client

    def generate(self, topic: dict, target_minutes: int) -> ContentPackage:
        memory = self.memory_store.load_all()
        target_minutes = min(8, max(2, target_minutes))
        target_words = target_minutes * 135
        memory_json = json.dumps(memory, ensure_ascii=False, indent=2)
        prompt = f"""
Create an original English story for children that takes about {target_minutes} minutes
to read aloud (roughly {target_words} words). The story topic is {topic['title']!r}.
Use this creative angle: {topic.get('angle', '')!r}. The intended audience is
{topic.get('audience', 'children')!r}.

Persistent story memory:
{memory_json}

Requirements:
- Keep the language warm, clear, age-appropriate, and engaging.
- Avoid frightening detail, violence, unsafe imitation, mature themes, brands, and
  copyrighted characters.
- Give the story a satisfying beginning, middle, and ending with a gentle positive lesson.
- Treat persistent memory as canon. Preserve every established character's name,
  appearance, personality, possessions, relationships, and history.
- Do not contradict world rules, locations, relationships, or timeline events.
- Existing facts may only be extended by events that happen in this story.
- Split it into exactly 8 scenes.
- Return only valid JSON with exactly these keys:
  "title" (string), "description" (string), "tags" (array of 3-7 English strings),
  "scenes" (array of objects with "narration", "visual_prompt", and "speech"), and
  "memory" (object containing exactly "characters", "world", "timeline",
  "locations", "inventory", and "relationships").
- The memory object must contain the complete canon after this story, including all
  prior facts and new important events. Timeline events must remain in chronological order.
- Each scene's "speech" must be an ordered array of objects with exactly "speaker"
  and "text". Allowed speakers are narrator, leo, scout, mother, and father.
- Split all spoken scene text into speech entries. Use narrator for narration and the
  matching character role for dialogue. The combined speech text must cover the scene.
- Each visual_prompt must describe an original, child-friendly illustration in English.
- Put the full story only in the scene narration fields; do not add markdown.
""".strip()

        response = self._get_client().responses.create(
            model=self.model,
            input=prompt,
        )
        try:
            data = json.loads(response.output_text)
            raw_scenes = data["scenes"]
            if len(raw_scenes) != 8:
                raise ValueError("Hikâye tam olarak 8 sahne içermelidir.")

            narrations = [str(item["narration"]).strip() for item in raw_scenes]
            total_words = sum(max(1, len(text.split())) for text in narrations)
            total_seconds = target_minutes * 60
            scenes = [
                Scene(
                    number=index,
                    narration=narration,
                    visual_prompt=str(raw["visual_prompt"]).strip(),
                    duration_seconds=max(
                        5, round(total_seconds * len(narration.split()) / total_words)
                    ),
                    speech=[
                        {
                            "speaker": str(segment["speaker"]).strip().lower(),
                            "text": str(segment["text"]).strip(),
                        }
                        for segment in raw.get(
                            "speech",
                            [{"speaker": "narrator", "text": narration}],
                        )
                        if str(segment.get("text", "")).strip()
                    ],
                )
                for index, (raw, narration) in enumerate(
                    zip(raw_scenes, narrations), start=1
                )
            ]
            content = ContentPackage(
                topic=topic["title"],
                title=str(data["title"]).strip(),
                description=str(data["description"]).strip(),
                tags=[str(tag).strip() for tag in data["tags"]],
                script="\n\n".join(narrations),
                scenes=scenes,
            )
            updated_memory = data["memory"]
            if not isinstance(updated_memory, dict):
                raise ValueError("Hafıza güncellemesi nesne olmalıdır.")
            self.memory_store.update(updated_memory)
            return content
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("OpenAI geçerli hikâye verisi döndürmedi.") from exc
