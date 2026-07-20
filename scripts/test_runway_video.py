from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from animation.models import SceneAnimation
from animation.runway_provider import RunwayVideoProvider
from src.config import ROOT, settings


REFERENCE_IMAGE = (
    ROOT
    / "data"
    / "projects"
    / "20260718-193119-gizemli-kayip-sehirler"
    / "images"
    / "scene_01.png"
)
OUTPUT_VIDEO = ROOT / "output" / "runway_test" / "leo_scout_scene_01.mp4"


def main() -> int:
    scene = SceneAnimation(
        image_path=REFERENCE_IMAGE,
        animation_prompt=(
            "Wholesome polished 3D family animation. Scout makes one small "
            "playful hop while balancing the acorn. Leo smiles, blinks, and "
            "turns slightly toward Scout. Leaves and warm sunbeams move gently. "
            "Preserve the exact faces, clothing, colors, proportions, character "
            "identities, environment, and art style from the reference image."
        ),
        duration=5,
        camera_motion="slow cinematic push-in with stable framing",
        output_video=OUTPUT_VIDEO,
    )
    provider = RunwayVideoProvider.from_settings(settings)
    result = provider.generate_scene(scene)
    if result.status != "generated":
        print(f"Runway test skipped/failed: {result.error}")
        return 1

    size = result.output_video.stat().st_size
    print(f"Runway test succeeded: {result.output_video.resolve()}")
    print(f"File size: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
