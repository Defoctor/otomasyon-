from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    repository = request.app.state.web_repository
    totals = repository.dashboard_counts()
    episodes = repository.list_episodes()
    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "totals": totals,
            "episodes": episodes[:5],
            "system": request.app.state.system_status(),
            "jobs": repository.recent_jobs(10),
            "poll_interval": request.app.state.settings.web_poll_interval_ms,
        },
    )


@router.get("/episodes", response_class=HTMLResponse)
def episode_list(request: Request, status: str = "all"):
    episodes = request.app.state.web_repository.list_episodes(status)
    return request.app.state.templates.TemplateResponse(
        request,
        "episodes.html",
        {"episodes": episodes, "selected_filter": status},
    )


@router.get("/episodes/{episode_id}", response_class=HTMLResponse)
def episode_detail(request: Request, episode_id: str):
    service = request.app.state.episode_service
    try:
        detail = service.detail(episode_id)
    except KeyError:
        return request.app.state.templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Episode not found", "message": episode_id},
            status_code=404,
        )
    return request.app.state.templates.TemplateResponse(
        request,
        "episode_detail.html",
        {"detail": detail},
    )
