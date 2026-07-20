from fastapi import APIRouter, HTTPException, Request, status

from app.web.schemas import (
    ActionResponse,
    DeleteMediaRequest,
    GenerateEpisodeRequest,
    EpisodeDetailResponse,
    EpisodeSummaryResponse,
    JobResponse,
    RejectRequest,
)
from app.web.security import validate_episode_id, validate_scene_number


router = APIRouter(prefix="/api", tags=["episodes"])
action_router = APIRouter(tags=["episode actions"])


@router.get("/episodes", response_model=list[EpisodeSummaryResponse])
def api_episodes(request: Request, status: str = "all"):
    return request.app.state.web_repository.list_episodes(status)


@router.get("/episodes/{episode_id}", response_model=EpisodeDetailResponse)
def api_episode_detail(request: Request, episode_id: str):
    validate_episode_id(episode_id)
    try:
        return request.app.state.episode_service.detail(episode_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@action_router.post(
    "/episodes/generate",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_episode_api(request: Request, payload: GenerateEpisodeRequest):
    try:
        return request.app.state.job_manager.submit_generate(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@action_router.post(
    "/episodes/{episode_id}/approve",
    response_model=ActionResponse,
)
def approve_episode(request: Request, episode_id: str):
    validate_episode_id(episode_id)
    _require_episode(request, episode_id)
    request.app.state.web_repository.approve(episode_id)
    return ActionResponse(
        episode_id=episode_id,
        approval_status="approved",
        upload_status="not_ready",
        message="Episode approved locally. No upload was performed.",
    )


@action_router.post(
    "/episodes/{episode_id}/reject",
    response_model=ActionResponse,
)
def reject_episode(
    request: Request, episode_id: str, payload: RejectRequest
):
    validate_episode_id(episode_id)
    _require_episode(request, episode_id)
    request.app.state.web_repository.reject(episode_id, payload.reason)
    return ActionResponse(
        episode_id=episode_id,
        approval_status="rejected",
        upload_status="not_ready",
        message="Episode rejected locally.",
    )


@action_router.post(
    "/episodes/{episode_id}/regenerate",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def regenerate_full(request: Request, episode_id: str):
    validate_episode_id(episode_id)
    _require_episode(request, episode_id)
    try:
        return request.app.state.job_manager.submit_operation(
            "regenerate_full",
            episode_id,
            {"episode_id": episode_id},
            staging_directory=str(
                request.app.state.settings.output_dir / ".staging"
            ),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@action_router.post(
    "/episodes/{episode_id}/scenes/{scene_number}/regenerate",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def regenerate_scene(
    request: Request, episode_id: str, scene_number: int
):
    validate_episode_id(episode_id)
    validate_scene_number(scene_number)
    _require_episode(request, episode_id)
    try:
        return request.app.state.job_manager.submit_operation(
            "regenerate_scene",
            episode_id,
            {
                "episode_id": episode_id,
                "scene_number": scene_number,
            },
            scene_number=scene_number,
            staging_directory=str(
                request.app.state.settings.output_dir / ".staging"
            ),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@action_router.post(
    "/episodes/{episode_id}/media/delete",
    response_model=ActionResponse,
)
def delete_generated_media(
    request: Request,
    episode_id: str,
    payload: DeleteMediaRequest,
):
    validate_episode_id(episode_id)
    _require_episode(request, episode_id)
    deleted = (
        request.app.state.job_manager.regeneration.delete_generated_media(
            episode_id
        )
    )
    return ActionResponse(
        episode_id=episode_id,
        approval_status="pending",
        upload_status="not_ready",
        message=(
            "Generated media deleted: " + ", ".join(deleted)
            if deleted
            else "No generated media was present."
        ),
    )


def _require_episode(request: Request, episode_id: str) -> None:
    if not request.app.state.web_repository.episode_exists(episode_id):
        raise HTTPException(
            status_code=404, detail=f"Episode not found: {episode_id}"
        )
