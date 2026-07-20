import json
from pathlib import Path
from types import SimpleNamespace

from app.quality.inspector import QualityInspector


def test_quality_report_records_all_critical_checks(
    tmp_path: Path, monkeypatch
):
    files = {
        name: tmp_path / name
        for name in [
            "final.mp4",
            "narration.wav",
            "music.wav",
            "subtitles.srt",
            "subtitles.ass",
        ]
    }
    for path in files.values():
        path.write_bytes(b"x" * 200_000)
    files["subtitles.srt"].write_text(
        "1\n00:00:00,000 --> 00:00:30,000\nA safe subtitle.\n",
        encoding="utf-8",
    )
    files["subtitles.ass"].write_text(
        "Dialogue: 0,0:00:00.00,0:00:30.00,Default,,0,0,0,,"
        r"A safe subtitle.",
        encoding="utf-8",
    )
    images = [tmp_path / f"scene_{index}.png" for index in range(6)]
    clips = [tmp_path / f"scene_{index}.mp4" for index in range(6)]
    for path in images + clips:
        path.write_bytes(b"asset")

    monkeypatch.setattr(
        "app.quality.inspector.probe_media",
        lambda path, ffprobe: {
            "format": {"duration": "30.0", "size": "200000"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        },
    )
    monkeypatch.setattr(
        "app.quality.inspector.run_checked",
        lambda *args, **kwargs: SimpleNamespace(stdout="", stderr=""),
    )
    report_path = tmp_path / "quality_report.json"

    report = QualityInspector(Path("ffmpeg"), Path("ffprobe")).inspect(
        "episode_0001",
        files["final.mp4"],
        30,
        images,
        clips,
        files["narration.wav"],
        files["music.wav"],
        files["subtitles.srt"],
        files["subtitles.ass"],
        report_path,
    )

    assert report["status"] == "passed"
    assert report["critical_errors"] == []
    assert report["checks"]["resolution"] is True
    assert report["checks"]["audio_stream"] is True
    assert report["checks"]["subtitle_placeholder_no_overlap"] is True
    assert report["checks"]["subtitle_max_two_lines"] is True
    assert report["checks"]["scenes_visually_distinct"] is True
    assert report["checks"]["demo_label_absent"] is True
    assert report["checks"]["character_bible_text_absent"] is True
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "passed"
