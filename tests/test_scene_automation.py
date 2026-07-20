import json
from pathlib import Path
from tempfile import TemporaryDirectory

from animation.models import AnimationResult, SceneAnimation
from animation.provider import VideoProvider
from animation.scene_pipeline import SceneProduction, SceneProductionPipeline
from src.models import ContentPackage, Scene
from src.scene_planner import split_into_short_scenes


class SequencedProvider(VideoProvider):
    provider_name = "test"

    def __init__(self, failures_before_success=0):
        self.calls = 0
        self.failures_before_success = failures_before_success

    def generate_scene(self, scene):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            return AnimationResult(scene, "failed", ["test"], error="temporary")
        scene.output_video.parent.mkdir(parents=True, exist_ok=True)
        scene.output_video.write_bytes(b"video")
        return AnimationResult(
            scene, "generated", ["test"], scene.output_video
        )


def test_story_sections_are_split_into_five_to_eight_second_scenes():
    content = ContentPackage(
        topic="test",
        title="Test",
        description="Test",
        tags=[],
        script="",
        scenes=[
            Scene(
                1,
                " ".join(f"word{i}" for i in range(40)),
                "Leo and Scout walk through the forest.",
                21,
            )
        ],
    )

    planned = split_into_short_scenes(content)

    assert [scene.duration_seconds for scene in planned.scenes] == [7, 7, 7]
    assert [scene.number for scene in planned.scenes] == [1, 2, 3]
    assert "word0" in planned.scenes[0].narration
    assert "word39" in planned.scenes[-1].narration


def test_scene_pipeline_retries_failure_and_skips_completed_clip():
    with TemporaryDirectory(dir=Path.cwd()) as directory:
        root = Path(directory)
        master = root / "images" / "scene_01.png"
        output = root / "animated_clips" / "scene_01.mp4"
        animation = SceneAnimation(
            master, "Gentle motion.", 6, "slow push-in", output
        )
        production = SceneProduction(1, master, "Master prompt", animation)
        pipeline = SceneProductionPipeline(root, [production], max_attempts=3)

        pipeline.prepare_master_frames(
            lambda scene: (
                scene.master_frame.parent.mkdir(parents=True, exist_ok=True),
                scene.master_frame.write_bytes(b"image"),
            )
            and True
        )
        provider = SequencedProvider(failures_before_success=1)
        results = pipeline.generate_clips(provider)

        assert results[-1].status == "generated"
        assert provider.calls == 2
        manifest = json.loads(
            pipeline.manifest_path.read_text(encoding="utf-8")
        )
        assert manifest["scenes"]["1"]["status"] == "completed"
        assert manifest["scenes"]["1"]["attempts"] == 2

        resumed_provider = SequencedProvider()
        resumed = SceneProductionPipeline(root, [production], max_attempts=3)
        resumed.generate_clips(resumed_provider)
        assert resumed_provider.calls == 0
