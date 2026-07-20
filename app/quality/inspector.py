import json
from pathlib import Path

from app.rendering.ffmpeg import probe_media, run_checked


class QualityInspector:
    def __init__(self, ffmpeg_path: Path, ffprobe_path: Path):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def inspect(
        self,
        episode_id: str,
        final_video: Path,
        story_duration: int,
        images: list[Path],
        clips: list[Path],
        narration: Path,
        music: Path,
        srt_path: Path,
        ass_path: Path,
        report_path: Path,
        expected_width: int = 1080,
        expected_height: int = 1920,
        expected_fps: int = 30,
        placeholder_contains_text: bool = False,
        visual_difference_score: float = 1.0,
    ) -> dict:
        critical_errors: list[str] = []
        warnings: list[str] = []
        checks: dict[str, bool] = {}

        checks["final_file_exists"] = _valid_file(final_video)
        checks["scene_count"] = len(images) == 6 and len(clips) == 6
        checks["all_images_exist"] = all(_valid_file(path) for path in images)
        checks["all_clips_exist"] = all(_valid_file(path) for path in clips)
        checks["narration_exists"] = _valid_file(narration)
        checks["music_exists"] = _valid_file(music)
        checks["subtitles_created"] = _valid_file(srt_path) and _valid_file(
            ass_path
        )
        srt_content = (
            srt_path.read_text(encoding="utf-8")
            if _valid_file(srt_path)
            else ""
        )
        ass_content = (
            ass_path.read_text(encoding="utf-8")
            if _valid_file(ass_path)
            else ""
        )
        dialogue_lines = [
            line
            for line in ass_content.splitlines()
            if line.startswith("Dialogue:")
        ]
        forbidden_presentation_text = (
            "CHARACTER LOCK",
            "CHARACTER BIBLE",
            "SCENE 1",
            "• DEMO",
        )
        checks["subtitle_placeholder_no_overlap"] = (
            not placeholder_contains_text
        )
        checks["subtitle_max_two_lines"] = bool(
            dialogue_lines
            and all(line.count(r"\N") <= 1 for line in dialogue_lines)
        )
        checks["scenes_visually_distinct"] = visual_difference_score >= 0.025
        checks["demo_label_absent"] = (
            not placeholder_contains_text
            and "DEMO" not in srt_content.upper()
            and "DEMO" not in ass_content.upper()
        )
        checks["character_bible_text_absent"] = (
            not placeholder_contains_text
            and not any(
                term in srt_content.upper() or term in ass_content.upper()
                for term in forbidden_presentation_text[:2]
            )
        )
        checks["no_zero_byte_assets"] = all(
            _valid_file(path)
            for path in [
                final_video,
                *images,
                *clips,
                narration,
                music,
                srt_path,
                ass_path,
            ]
        )

        probe = {}
        if checks["final_file_exists"]:
            try:
                probe = probe_media(final_video, self.ffprobe_path)
            except Exception as exc:
                critical_errors.append(f"FFprobe failed: {type(exc).__name__}: {exc}")
        streams = probe.get("streams", [])
        video = next(
            (item for item in streams if item.get("codec_type") == "video"),
            None,
        )
        audio = next(
            (item for item in streams if item.get("codec_type") == "audio"),
            None,
        )
        duration = float(probe.get("format", {}).get("duration", 0) or 0)

        checks["video_stream"] = video is not None
        checks["audio_stream"] = audio is not None
        checks["resolution"] = bool(
            video
            and video.get("width") == expected_width
            and video.get("height") == expected_height
        )
        checks["vertical_9_16"] = bool(
            video
            and int(video.get("width", 0)) * 16
            == int(video.get("height", 0)) * 9
        )
        checks["fps"] = bool(
            video and _fps(video.get("r_frame_rate", "0/1")) == expected_fps
        )
        checks["duration_in_shorts_range"] = 25 <= duration <= 35
        checks["duration_matches_story"] = abs(duration - story_duration) <= 0.35
        checks["video_codec"] = bool(
            video and video.get("codec_name") in {"h264", "avc1"}
        )
        checks["audio_codec"] = bool(
            audio and audio.get("codec_name") in {"aac", "mp3", "opus"}
        )
        checks["audio_sample_rate"] = bool(
            audio and audio.get("sample_rate") == "48000"
        )
        checks["subtitles_burned_in"] = (
            checks["subtitles_created"] and checks["video_stream"]
        )
        checks["reasonable_file_size"] = bool(
            checks["final_file_exists"]
            and 100_000 <= final_video.stat().st_size <= 500_000_000
        )

        critical_names = [
            "final_file_exists",
            "scene_count",
            "all_images_exist",
            "all_clips_exist",
            "narration_exists",
            "music_exists",
            "subtitles_created",
            "subtitle_placeholder_no_overlap",
            "subtitle_max_two_lines",
            "scenes_visually_distinct",
            "demo_label_absent",
            "character_bible_text_absent",
            "no_zero_byte_assets",
            "video_stream",
            "audio_stream",
            "resolution",
            "vertical_9_16",
            "fps",
            "duration_in_shorts_range",
            "duration_matches_story",
            "video_codec",
            "audio_codec",
            "audio_sample_rate",
            "subtitles_burned_in",
            "reasonable_file_size",
        ]
        critical_errors.extend(
            f"Critical quality check failed: {name}"
            for name in critical_names
            if not checks.get(name, False)
        )

        black_detected = False
        if checks["video_stream"]:
            try:
                result = run_checked(
                    [
                        str(self.ffmpeg_path),
                        "-hide_banner",
                        "-i",
                        str(final_video),
                        "-vf",
                        "blackdetect=d=0.5:pix_th=0.98",
                        "-an",
                        "-f",
                        "null",
                        "NUL",
                    ],
                    "Black-frame inspection",
                )
                black_detected = "black_start:" in (
                    (result.stderr or "") + (result.stdout or "")
                )
            except Exception as exc:
                warnings.append(
                    f"Black-frame analysis unavailable: {type(exc).__name__}: {exc}"
                )
        checks["black_frame_risk"] = not black_detected
        if black_detected:
            warnings.append("FFmpeg detected a possible black segment.")

        report = {
            "episode_id": episode_id,
            "status": "passed" if not critical_errors else "failed",
            "critical_errors": critical_errors,
            "warnings": warnings,
            "checks": checks,
            "measured": {
                "duration_seconds": round(duration, 3),
                "width": video.get("width") if video else None,
                "height": video.get("height") if video else None,
                "fps": _fps(video.get("r_frame_rate", "0/1")) if video else None,
                "video_codec": video.get("codec_name") if video else None,
                "audio_codec": audio.get("codec_name") if audio else None,
                "audio_sample_rate": audio.get("sample_rate") if audio else None,
                "file_size_bytes": (
                    final_video.stat().st_size
                    if checks["final_file_exists"]
                    else 0
                ),
                "visual_difference_score": round(
                    visual_difference_score, 4
                ),
            },
        }
        _atomic_json(report_path, report)
        return report


def _valid_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _fps(value: str) -> float:
    numerator, denominator = value.split("/", 1)
    return round(float(numerator) / max(float(denominator), 1), 3)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
