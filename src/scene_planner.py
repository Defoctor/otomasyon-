from dataclasses import replace
import math

from src.models import ContentPackage, Scene


def split_into_short_scenes(
    content: ContentPackage,
    minimum_seconds: int = 5,
    maximum_seconds: int = 8,
) -> ContentPackage:
    """Expand story sections into deterministic, production-sized shots."""
    if minimum_seconds < 1 or maximum_seconds < minimum_seconds:
        raise ValueError("Scene duration range is invalid.")

    planned: list[Scene] = []
    for source in content.scenes:
        duration = max(minimum_seconds, source.duration_seconds)
        part_count = max(1, math.ceil(duration / maximum_seconds))
        while part_count > 1 and duration / part_count < minimum_seconds:
            part_count -= 1

        narration_parts = _split_words(source.narration, part_count)
        speech_parts = _split_speech(source.speech, len(narration_parts))
        durations = _distribute_duration(
            duration, len(narration_parts), minimum_seconds, maximum_seconds
        )
        for part_index, (narration, part_duration) in enumerate(
            zip(narration_parts, durations), start=1
        ):
            planned.append(
                Scene(
                    number=len(planned) + 1,
                    narration=narration,
                    visual_prompt=(
                        f"{source.visual_prompt} "
                        f"Continuous shot {part_index} of {len(narration_parts)}."
                    ),
                    duration_seconds=part_duration,
                    speech=(
                        speech_parts[part_index - 1]
                        or [{"speaker": "narrator", "text": narration}]
                    ),
                )
            )

    return replace(
        content,
        script="\n\n".join(scene.narration for scene in planned),
        scenes=planned,
    )


def _split_words(text: str, count: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    count = min(count, len(words))
    base, extra = divmod(len(words), count)
    result = []
    offset = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        result.append(" ".join(words[offset : offset + size]))
        offset += size
    return result


def _split_speech(
    speech: list[dict[str, str]], count: int
) -> list[list[dict[str, str]]]:
    tokens = [
        (str(item.get("speaker", "narrator")), word)
        for item in speech
        for word in str(item.get("text", "")).split()
    ]
    if not tokens:
        return [[] for _ in range(count)]
    base, extra = divmod(len(tokens), count)
    chunks: list[list[dict[str, str]]] = []
    offset = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        grouped: list[dict[str, str]] = []
        for speaker, word in tokens[offset : offset + size]:
            if grouped and grouped[-1]["speaker"] == speaker:
                grouped[-1]["text"] += f" {word}"
            else:
                grouped.append({"speaker": speaker, "text": word})
        chunks.append(grouped)
        offset += size
    return chunks


def _distribute_duration(
    total: int, count: int, minimum: int, maximum: int
) -> list[int]:
    if count == 1:
        return [min(maximum, max(minimum, total))]
    base, extra = divmod(total, count)
    durations = [base + (1 if index < extra else 0) for index in range(count)]
    return [min(maximum, max(minimum, value)) for value in durations]
