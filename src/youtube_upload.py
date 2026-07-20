import json
from pathlib import Path

from src.config import settings


def prepare_upload_package(
    project_dir: Path,
    content,
    video_path: Path | None,
    shorts_path: Path | None,
) -> Path:
    manifest = {
        "title": content.title,
        "description": content.description,
        "tags": content.tags,
        "category": "Education",
        "language": "en",
        "made_for_kids": True,
        "privacy_status": "private",
        "main_video": str(video_path) if video_path else None,
        "shorts_video": str(shorts_path) if shorts_path else None,
        "thumbnail": str(project_dir / "thumbnail.png"),
        "requires_human_approval": True,
        "youtube_uploaded": False,
        "assets_complete": bool(
            video_path
            and video_path.exists()
            and shorts_path
            and shorts_path.exists()
            and (project_dir / "thumbnail.png").exists()
        ),
    }
    output = project_dir / "youtube_ready.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def upload_video(video_path: Path, metadata: dict, human_approved: bool) -> str:
    """Bilinçli olarak kapalı güvenlik kapısı.

    Gerçek YouTube Data API istemcisi ayrı bir sonraki aşamada eklenebilir.
    Hem ortam değişkeni hem insan onayı olmadan çalışmaz.
    """
    if not settings.youtube_upload_enabled:
        raise RuntimeError("YouTube yükleme .env içinde kapalı.")
    if not human_approved:
        raise RuntimeError("İnsan onayı olmadan YouTube'a yükleme yapılamaz.")
    raise NotImplementedError(
        "YouTube API bağlantısı bu güvenli MVP'de etkin değil; yalnızca arayüzü hazır."
    )
