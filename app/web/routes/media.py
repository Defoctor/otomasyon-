import mimetypes

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.web.security import safe_media_path


router = APIRouter(tags=["media"])


@router.get("/media/{episode_id}/{path:path}", name="media_file")
def media_file(request: Request, episode_id: str, path: str):
    candidate = safe_media_path(
        request.app.state.settings.output_dir, episode_id, path
    )
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")
    media_type, _ = mimetypes.guess_type(candidate.name)
    return FileResponse(
        candidate,
        media_type=media_type or "application/octet-stream",
        filename=None,
    )
