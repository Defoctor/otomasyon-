from pathlib import Path

from PIL import Image, ImageDraw

from app.providers.base import ImageProvider
from app.schemas.story import MainCharacter, Scene, StoryCategory


SCENE_BACKGROUNDS = [
    ("#355C8A", "#FFCB77"),
    ("#3E6B88", "#FFD38E"),
    ("#47778A", "#B8E0D2"),
    ("#568477", "#CDE7BE"),
    ("#638D73", "#FFE29A"),
    ("#536F91", "#FFD6A5"),
]


class PlaceholderImageProvider(ImageProvider):
    """Draw a text-free story storyboard with consistent character styling."""

    provider_name = "placeholder"
    contains_text = False

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height

    def generate_scene(
        self,
        scene: Scene,
        character: MainCharacter,
        story_category: StoryCategory,
        output_path: Path,
    ) -> Path:
        background, glow = SCENE_BACKGROUNDS[
            (scene.scene_number - 1) % len(SCENE_BACKGROUNDS)
        ]
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)
        self._draw_atmosphere(draw, scene.scene_number, glow)
        self._draw_story_scene(draw, scene.scene_number)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(output_path)
        return output_path

    def _draw_atmosphere(
        self, draw: ImageDraw.ImageDraw, scene_number: int, glow: str
    ) -> None:
        w, h = self.width, self.height
        draw.ellipse(
            (
                int(w * 0.55),
                int(h * 0.04),
                int(w * 1.08),
                int(h * 0.34),
            ),
            fill=glow,
        )
        hill_colors = ["#7FB069", "#76A867", "#6DA064"]
        draw.ellipse(
            (-int(w * 0.35), int(h * 0.55), int(w * 0.75), int(h * 1.08)),
            fill=hill_colors[scene_number % 3],
        )
        draw.ellipse(
            (int(w * 0.35), int(h * 0.60), int(w * 1.35), int(h * 1.10)),
            fill="#659A61",
        )
        for index in range(7):
            x = int(w * (0.05 + index * 0.15))
            y = int(h * (0.50 + (index % 2) * 0.035))
            draw.ellipse(
                (x, y, x + int(w * 0.035), y + int(w * 0.035)),
                fill="#FFF3B0",
            )

    def _draw_story_scene(
        self, draw: ImageDraw.ImageDraw, scene_number: int
    ) -> None:
        w, h = self.width, self.height
        if scene_number == 1:
            _cloud(draw, w * 0.58, h * 0.12, w * 0.34)
            _bell(draw, w * 0.58, h * 0.34, w * 0.28, rotation=-8)
            _rabbit(
                draw,
                w * 0.28,
                h * 0.66,
                w * 0.24,
                facing=1,
                surprised=True,
            )
            _motion_lines(draw, w * 0.58, h * 0.35, w * 0.22)
        elif scene_number == 2:
            _rabbit(draw, w * 0.25, h * 0.64, w * 0.20, facing=1)
            _duckling(draw, w * 0.68, h * 0.69, w * 0.13, facing=-1)
            _bell(draw, w * 0.57, h * 0.36, w * 0.10)
            _sparkles(draw, w * 0.58, h * 0.42, w * 0.22)
        elif scene_number == 3:
            _puddle(draw, w * 0.50, h * 0.72, w * 0.78, h * 0.16)
            _rabbit(draw, w * 0.20, h * 0.58, w * 0.18, facing=1)
            _duckling(draw, w * 0.42, h * 0.68, w * 0.11, facing=1)
            _duckling(draw, w * 0.78, h * 0.63, w * 0.09, facing=-1)
            _duckling(draw, w * 0.88, h * 0.66, w * 0.08, facing=-1)
        elif scene_number == 4:
            _puddle(draw, w * 0.53, h * 0.73, w * 0.82, h * 0.18)
            _rabbit(draw, w * 0.23, h * 0.60, w * 0.19, facing=1)
            for index in range(4):
                _leaf(
                    draw,
                    w * (0.40 + index * 0.13),
                    h * (0.70 - (index % 2) * 0.018),
                    w * 0.105,
                    angle=(-12 + index * 8),
                )
            _duckling(draw, w * 0.83, h * 0.61, w * 0.10, facing=-1)
        elif scene_number == 5:
            _rabbit(draw, w * 0.24, h * 0.65, w * 0.18, facing=1)
            _duckling(draw, w * 0.57, h * 0.68, w * 0.12, facing=-1)
            _duckling(draw, w * 0.75, h * 0.65, w * 0.10, facing=-1)
            _duckling(draw, w * 0.87, h * 0.67, w * 0.085, facing=-1)
            _bell(draw, w * 0.58, h * 0.31, w * 0.15)
            _sparkles(draw, w * 0.58, h * 0.38, w * 0.34)
        else:
            _rabbit(draw, w * 0.25, h * 0.69, w * 0.16, facing=1)
            _duckling(draw, w * 0.46, h * 0.72, w * 0.09, facing=1)
            _cloud(draw, w * 0.66, h * 0.13, w * 0.30)
            _bell(draw, w * 0.66, h * 0.27, w * 0.11)
            _sparkles(draw, w * 0.63, h * 0.35, w * 0.20)


def _rabbit(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    facing: int,
    surprised: bool = False,
) -> None:
    fur = "#B9A7D1"
    white = "#F7F3FA"
    outline = "#514861"
    overall = "#73C8A9"
    direction = 1 if facing >= 0 else -1
    left = x - size * 0.5
    top = y - size * 0.75
    draw.ellipse(
        (left, y - size * 0.15, left + size, y + size * 0.85),
        fill=fur,
        outline=outline,
        width=max(2, int(size * 0.025)),
    )
    head_x = x + direction * size * 0.12
    draw.ellipse(
        (
            head_x - size * 0.43,
            top,
            head_x + size * 0.43,
            top + size * 0.78,
        ),
        fill=fur,
        outline=outline,
        width=max(2, int(size * 0.025)),
    )
    for ear_offset, fold in [(-0.20, False), (0.19, True)]:
        ear_x = head_x + size * ear_offset
        ear_top = top - size * (0.62 if not fold else 0.49)
        draw.ellipse(
            (
                ear_x - size * 0.13,
                ear_top,
                ear_x + size * 0.13,
                top + size * 0.14,
            ),
            fill=fur,
            outline=outline,
            width=max(2, int(size * 0.02)),
        )
        draw.ellipse(
            (
                ear_x - size * 0.055,
                ear_top + size * 0.08,
                ear_x + size * 0.055,
                top + size * 0.05,
            ),
            fill="#E8C7D8",
        )
    draw.rounded_rectangle(
        (
            left + size * 0.12,
            y + size * 0.10,
            left + size * 0.88,
            y + size * 0.62,
        ),
        radius=int(size * 0.10),
        fill=overall,
    )
    eye_x = head_x + direction * size * 0.19
    eye_radius = size * (0.075 if surprised else 0.06)
    draw.ellipse(
        (
            eye_x - eye_radius,
            top + size * 0.28 - eye_radius,
            eye_x + eye_radius,
            top + size * 0.28 + eye_radius,
        ),
        fill=white,
        outline=outline,
        width=max(2, int(size * 0.018)),
    )
    pupil = eye_radius * 0.46
    draw.ellipse(
        (
            eye_x + direction * pupil * 0.25 - pupil,
            top + size * 0.28 - pupil,
            eye_x + direction * pupil * 0.25 + pupil,
            top + size * 0.28 + pupil,
        ),
        fill="#527A60",
    )
    mouth_y = top + size * 0.52
    if surprised:
        draw.ellipse(
            (
                head_x + direction * size * 0.15 - size * 0.045,
                mouth_y - size * 0.045,
                head_x + direction * size * 0.15 + size * 0.045,
                mouth_y + size * 0.045,
            ),
            fill=outline,
        )
    else:
        draw.arc(
            (
                head_x + direction * size * 0.05 - size * 0.10,
                mouth_y - size * 0.05,
                head_x + direction * size * 0.05 + size * 0.10,
                mouth_y + size * 0.08,
            ),
            10,
            165,
            fill=outline,
            width=max(2, int(size * 0.018)),
        )


def _bell(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    rotation: float = 0,
) -> None:
    del rotation
    silver = "#DCE5EC"
    dark = "#647887"
    draw.arc(
        (x - size * 0.14, y - size * 0.72, x + size * 0.14, y - size * 0.38),
        180,
        360,
        fill=dark,
        width=max(3, int(size * 0.05)),
    )
    draw.polygon(
        [
            (x - size * 0.30, y - size * 0.40),
            (x + size * 0.30, y - size * 0.40),
            (x + size * 0.44, y + size * 0.35),
            (x - size * 0.44, y + size * 0.35),
        ],
        fill=silver,
        outline=dark,
    )
    draw.ellipse(
        (x - size * 0.50, y + size * 0.25, x + size * 0.50, y + size * 0.48),
        fill="#EEF4F7",
        outline=dark,
        width=max(2, int(size * 0.035)),
    )
    draw.ellipse(
        (x - size * 0.10, y + size * 0.38, x + size * 0.10, y + size * 0.62),
        fill="#93A4AF",
    )


def _duckling(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    facing: int,
) -> None:
    direction = 1 if facing >= 0 else -1
    draw.ellipse(
        (x - size * 0.45, y, x + size * 0.45, y + size * 0.65),
        fill="#FFD84D",
        outline="#A66B15",
        width=max(2, int(size * 0.025)),
    )
    head_x = x + direction * size * 0.22
    draw.ellipse(
        (
            head_x - size * 0.30,
            y - size * 0.38,
            head_x + size * 0.30,
            y + size * 0.17,
        ),
        fill="#FFE36E",
        outline="#A66B15",
        width=max(2, int(size * 0.025)),
    )
    draw.polygon(
        [
            (head_x + direction * size * 0.28, y - size * 0.10),
            (head_x + direction * size * 0.52, y),
            (head_x + direction * size * 0.28, y + size * 0.07),
        ],
        fill="#F28C28",
    )
    draw.ellipse(
        (
            head_x + direction * size * 0.08 - size * 0.035,
            y - size * 0.18,
            head_x + direction * size * 0.08 + size * 0.035,
            y - size * 0.11,
        ),
        fill="#30343B",
    )


def _cloud(
    draw: ImageDraw.ImageDraw, x: float, y: float, size: float
) -> None:
    color = "#F7FAFC"
    for dx, dy, radius in [
        (-0.30, 0.08, 0.30),
        (0.0, -0.02, 0.38),
        (0.33, 0.08, 0.29),
    ]:
        draw.ellipse(
            (
                x + size * (dx - radius),
                y + size * (dy - radius),
                x + size * (dx + radius),
                y + size * (dy + radius),
            ),
            fill=color,
        )
    draw.rounded_rectangle(
        (
            x - size * 0.58,
            y,
            x + size * 0.60,
            y + size * 0.34,
        ),
        radius=int(size * 0.14),
        fill=color,
    )


def _puddle(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    draw.ellipse(
        (x - width / 2, y - height / 2, x + width / 2, y + height / 2),
        fill="#75C9E6",
        outline="#D4F1F9",
        width=max(3, int(height * 0.07)),
    )
    draw.arc(
        (x - width * 0.28, y - height * 0.22, x + width * 0.28, y + height * 0.22),
        8,
        172,
        fill="#EAFBFF",
        width=max(2, int(height * 0.035)),
    )


def _leaf(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    angle: float,
) -> None:
    del angle
    draw.ellipse(
        (x - size * 0.55, y - size * 0.25, x + size * 0.55, y + size * 0.25),
        fill="#78B547",
        outline="#3D6F2A",
        width=max(2, int(size * 0.025)),
    )
    draw.line(
        (x - size * 0.42, y, x + size * 0.42, y),
        fill="#3D6F2A",
        width=max(2, int(size * 0.02)),
    )


def _sparkles(
    draw: ImageDraw.ImageDraw, x: float, y: float, spread: float
) -> None:
    for dx, dy, scale in [
        (-0.9, -0.2, 0.12),
        (-0.45, 0.3, 0.08),
        (0.1, -0.4, 0.10),
        (0.55, 0.15, 0.13),
        (0.9, -0.1, 0.07),
    ]:
        px, py = x + dx * spread, y + dy * spread
        radius = spread * scale
        draw.polygon(
            [(px, py - radius), (px + radius * 0.35, py), (px, py + radius), (px - radius * 0.35, py)],
            fill="#FFF3A6",
        )


def _motion_lines(
    draw: ImageDraw.ImageDraw, x: float, y: float, size: float
) -> None:
    for offset in (-0.55, 0.0, 0.55):
        draw.arc(
            (
                x + offset * size - size * 0.40,
                y - size * 0.35,
                x + offset * size + size * 0.40,
                y + size * 0.35,
            ),
            205,
            330,
            fill="#F8F9FA",
            width=max(3, int(size * 0.025)),
        )
