from pathlib import Path

from app.schemas.story import Scene


def create_subtitles(
    scenes: list[Scene],
    srt_path: Path,
    ass_path: Path,
    width: int = 1080,
    height: int = 1920,
    font_name: str = "Arial",
) -> tuple[Path, Path]:
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    offsets = _scene_offsets(scenes)

    srt_blocks = []
    ass_events = []
    for scene, (start, end) in zip(scenes, offsets):
        lines = _two_lines(scene.narration, max_characters=40)
        srt_blocks.append(
            f"{scene.scene_number}\n"
            f"{_srt_time(start)} --> {_srt_time(end)}\n"
            f"{lines}\n"
        )
        ass_text = lines.replace("\n", r"\N")
        ass_events.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},"
            f"Default,,0,0,0,,{_escape_ass(ass_text)}"
        )

    _atomic_text(srt_path, "\n".join(srt_blocks).rstrip() + "\n")
    _atomic_text(
        ass_path,
        _ass_header(width, height, font_name)
        + "\n".join(ass_events)
        + "\n",
    )
    return srt_path, ass_path


def _scene_offsets(scenes: list[Scene]) -> list[tuple[float, float]]:
    result = []
    offset = 0.0
    for scene in scenes:
        end = offset + scene.duration_seconds
        result.append((offset, end))
        offset = end
    return result


def _two_lines(text: str, max_characters: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_characters:
        return normalized
    words = normalized.split()
    candidates = []
    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        longest = max(len(first), len(second))
        imbalance = abs(len(first) - len(second))
        overflow = max(0, longest - max_characters)
        candidates.append((overflow, imbalance, index, first, second))
    _, _, _, first, second = min(candidates)
    return f"{first}\n{second}"


def _srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centis:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("{", r"\{").replace("}", r"\}")


def _ass_header(width: int, height: int, font_name: str) -> str:
    margin_lr = round(width * 0.10)
    margin_vertical = round(height * 0.13)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},72,&H00FFFFFF,&H000000FF,&H00101820,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,2,{margin_lr},{margin_lr},{margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)
