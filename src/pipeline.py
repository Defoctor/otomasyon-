from datetime import datetime
import json
from pathlib import Path
import re

from src.config import settings
from src.providers import FakeContentProvider, FakeMediaProvider, FakeVoiceProvider
from src.thumbnail import create_thumbnail
from src.video import build_video


def load_topics() -> list[dict]:
    return json.loads(settings.topics_file.read_text(encoding="utf-8"))


def run_pipeline(topic: dict, target_minutes: int = 5) -> dict:
    content = FakeContentProvider().generate(topic, target_minutes)
    slug = re.sub(r"[^a-z0-9]+", "-", topic["id"].lower()).strip("-")
    project_dir = settings.projects_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    project_dir.mkdir(parents=True, exist_ok=False)

    (project_dir / "metadata.json").write_text(
        json.dumps(content.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (project_dir / "script.txt").write_text(content.script, encoding="utf-8")
    (project_dir / "approval_status.json").write_text(
        json.dumps(
            {"approved": False, "youtube_uploaded": False, "note": "İnsan kontrolü bekleniyor."},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    voice = FakeVoiceProvider()
    media = FakeMediaProvider()
    for scene in content.scenes:
        voice.synthesize(
            scene.narration,
            project_dir / "audio" / f"scene_{scene.number:02d}.wav",
            scene.duration_seconds,
        )
        media.create_scene(
            scene.visual_prompt,
            project_dir / "scenes" / f"scene_{scene.number:02d}.png",
            f"SAHNE {scene.number}",
        )

    create_thumbnail(content.title, project_dir / "thumbnail.png")
    video_path, message = build_video(project_dir, len(content.scenes))
    return {
        "project_dir": project_dir,
        "content": content,
        "video_path": video_path,
        "message": message,
    }

