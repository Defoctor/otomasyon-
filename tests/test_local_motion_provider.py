from pathlib import Path

from PIL import Image

from app.providers.video import LocalMotionVideoProvider
from app.rendering.ffmpeg import probe_media, resolve_media_tool


def test_media_tools_resolve_from_installation():
    assert resolve_media_tool("ffmpeg").name == "ffmpeg.exe"
    assert resolve_media_tool("ffprobe").name == "ffprobe.exe"


def test_local_motion_creates_timed_h264_clip(tmp_path: Path):
    image = tmp_path / "scene.png"
    Image.new("RGB", (320, 568), "#315A7D").save(image)
    output = tmp_path / "scene.mp4"
    provider = LocalMotionVideoProvider(
        resolve_media_tool("ffmpeg"),
        width=320,
        height=568,
        fps=30,
        preset="ultrafast",
    )

    provider.generate_scene(image, output, duration_seconds=1, scene_number=2)
    probe = probe_media(output, resolve_media_tool("ffprobe"))
    video = next(
        stream for stream in probe["streams"] if stream["codec_type"] == "video"
    )

    assert video["codec_name"] == "h264"
    assert (video["width"], video["height"]) == (320, 568)
    assert video["r_frame_rate"] == "30/1"
    assert abs(float(probe["format"]["duration"]) - 1.0) < 0.1
