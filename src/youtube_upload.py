from pathlib import Path

from src.config import settings


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

