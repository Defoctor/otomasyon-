from abc import ABC, abstractmethod
from pathlib import Path

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

