from pathlib import Path
from types import SimpleNamespace

from app.quality.inspector import QualityInspector


def test_presentation_quality_fails_for_placeholder_text_and_three_lines(
    tmp_path: Path, monkeypatch
):
    final = tmp_path / "final.mp4"
    narration = tmp_path / "narration.wav"
    music = tmp_path / "music.wav"
    srt = tmp_path / "subtitles.srt"
    ass = tmp_path / "subtitles.ass"
    for path in (final, narration, music):
        path.write_bytes(b"x" * 200_000)
    srt.write_text("1\n00:00:00,000 --> 00:00:30,000\nDEMO\n", encoding="utf-8")
    ass.write_text(
        "Dialogue: 0,0:00:00.00,0:00:30.00,Default,,0,0,0,,"
        r"one\Ntwo\Nthree",
        encoding="utf-8",
    )
    images = [tmp_path / f"image_{index}.png" for index in range(6)]
    clips = [tmp_path / f"clip_{index}.mp4" for index in range(6)]
    for path in images + clips:
        path.write_bytes(b"asset")
    monkeypatch.setattr(
        "app.quality.inspector.probe_media",
        lambda *args: {
            "format": {"duration": "30"},
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
                },
            ],
        },
    )
    monkeypatch.setattr(
        "app.quality.inspector.run_checked",
        lambda *args, **kwargs: SimpleNamespace(stdout="", stderr=""),
    )

    report = QualityInspector(Path("ffmpeg"), Path("ffprobe")).inspect(
        "episode_0001",
        final,
        30,
        images,
        clips,
        narration,
        music,
        srt,
        ass,
        tmp_path / "quality.json",
        placeholder_contains_text=True,
        visual_difference_score=0.0,
    )

    assert report["status"] == "failed"
    assert report["checks"]["subtitle_placeholder_no_overlap"] is False
    assert report["checks"]["subtitle_max_two_lines"] is False
    assert report["checks"]["scenes_visually_distinct"] is False
    assert report["checks"]["demo_label_absent"] is False
