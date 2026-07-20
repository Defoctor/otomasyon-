from abc import ABC, abstractmethod
import base64
import os
from pathlib import Path
import time
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont


class MediaProvider(ABC):
    @abstractmethod
    def create_scene(self, prompt: str, output_path: Path, label: str) -> Path:
        raise NotImplementedError


class FakeMediaProvider(MediaProvider):
    """Test için 1280x720 özgün yer tutucu görseller üretir."""

    def create_scene(self, prompt: str, output_path: Path, label: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (1280, 720), "#10263d")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=34)
        small = ImageFont.load_default(size=20)
        draw.rounded_rectangle((70, 70, 1210, 650), radius=32, fill="#173b5f")
        draw.text((110, 120), label, fill="#f4c95d", font=font)
        wrapped = _wrap(prompt, 70)
        draw.multiline_text((110, 220), wrapped, fill="white", font=small, spacing=12)
        draw.text((110, 600), "TEST GÖRSELİ • YAYINDAN ÖNCE DEĞİŞTİRİN", fill="#9fc5e8", font=small)
        image.save(output_path)
        return output_path


class OpenAIImageProvider(MediaProvider):
    """OpenAI Images API ile sahne görseli üretir."""

    def __init__(
        self,
        model: str,
        size: str,
        quality: str,
        client: Any | None = None,
    ):
        self.model = model
        self.size = size
        self.quality = quality
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MEDIA_PROVIDER=openai için .env dosyasında OPENAI_API_KEY tanımlanmalıdır."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        return self._client

    def create_scene(self, prompt: str, output_path: Path, label: str) -> Path:
        response = self._get_client().images.generate(
            model=self.model,
            prompt=prompt,
            size=self.size,
            quality=self.quality,
        )
        if not response.data or not response.data[0].b64_json:
            raise RuntimeError("OpenAI Images API boş görsel yanıtı döndürdü.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(response.data[0].b64_json))
        return output_path


class RunwayReferenceImageProvider(MediaProvider):
    """Create master frames with Gen-4 Image and up to three references."""

    def __init__(
        self,
        api_key: str,
        reference_images: list[Path],
        model: str = "gen4_image",
        ratio: str = "1280:720",
        poll_interval: float = 5,
        timeout: float = 300,
        client: Any | None = None,
    ):
        if model not in {"gen4_image", "gen4_image_turbo"}:
            raise ValueError("Runway master-frame model must be Gen-4 Image.")
        if len(reference_images) > 3:
            raise ValueError("Gen-4 Image accepts at most three references.")
        self.api_key = api_key
        self.reference_images = reference_images
        self.model = model
        self.ratio = ratio
        self.poll_interval = max(5, poll_interval)
        self.timeout = timeout
        self._client = client

    def create_scene(self, prompt: str, output_path: Path, label: str) -> Path:
        if not self.api_key:
            raise RuntimeError("RUNWAY_API_KEY is required for master frames.")
        if not self.reference_images:
            raise RuntimeError(
                "RUNWAY_REFERENCE_IMAGES must contain character references."
            )
        missing = [path for path in self.reference_images if not path.is_file()]
        if missing:
            raise RuntimeError(f"Runway reference image not found: {missing[0]}")
        references = [
            {"uri": _data_uri(path), "tag": _safe_tag(path.stem, index)}
            for index, path in enumerate(self.reference_images, start=1)
        ]
        identities = ", ".join(f"@{item['tag']}" for item in references)
        reference_prompt = (
            f"Preserve the exact identities and character designs of "
            f"{identities}. {prompt}"
        )
        task = self._get_client().text_to_image.create(
            model=self.model,
            prompt_text=reference_prompt[:1000],
            ratio=self.ratio,
            reference_images=references,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            current = self._get_client().tasks.retrieve(str(task.id))
            status = str(getattr(current, "status", "")).upper()
            if status == "SUCCEEDED":
                urls = getattr(current, "output", None) or []
                if not urls:
                    raise RuntimeError("Runway master-frame task has no output.")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_suffix(output_path.suffix + ".tmp")
                with urlopen(urls[0], timeout=120) as response:
                    temporary.write_bytes(response.read())
                temporary.replace(output_path)
                return output_path
            if status in {"FAILED", "CANCELED"}:
                failure = getattr(current, "failure", None)
                raise RuntimeError(
                    f"Runway master-frame task {status}: "
                    f"{failure or 'no details'}"
                )
            time.sleep(self.poll_interval)
        raise TimeoutError("Runway master-frame generation timed out.")

    def _get_client(self):
        if self._client is None:
            from runwayml import RunwayML

            self._client = RunwayML(api_key=self.api_key)
        return self._client


def _wrap(text: str, width: int) -> str:
    words, lines, current = text.split(), [], []
    for word in words:
        if len(" ".join(current + [word])) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def _data_uri(path: Path) -> str:
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _safe_tag(stem: str, index: int) -> str:
    tag = "".join(character for character in stem.lower() if character.isalnum())
    return (tag or f"reference{index}")[:16]
