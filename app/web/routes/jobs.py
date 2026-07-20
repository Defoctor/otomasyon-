from fastapi import APIRouter, HTTPException, Request

from app.web.schemas import JobResponse


router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def job_status(request: Request, job_id: str):
    try:
        return request.app.state.web_repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/jobs", response_model=list[JobResponse])
def recent_jobs(request: Request, limit: int = 20):
    return request.app.state.web_repository.recent_jobs(limit)
