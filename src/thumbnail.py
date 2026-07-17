from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def create_thumbnail(title: str, output_path: Path) -> Path:
    image = Image.new("RGB", (1280, 720), "#091a2a")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=54)
    badge_font = ImageFont.load_default(size=26)
    draw.ellipse((820, 40, 1320, 540), fill="#e65f5c")
    draw.rounded_rectangle((55, 55, 310, 110), 18, fill="#f4c95d")
    draw.text((80, 70), "KISA BELGESEL", fill="#091a2a", font=badge_font)
    draw.multiline_text((70, 190), _wrap(title.upper(), 25), fill="white", font=title_font, spacing=14)
    image.save(output_path)
    return output_path


def _wrap(text: str, width: int) -> str:
    words, lines, line = text.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return "\n".join(lines[:4])

