from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.common import ErrorResponse
from app.schemas.jobs import ResearchJobListResponse, ResearchJobResponse
from app.services.jobs import get_research_job, list_research_jobs, serialize_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    response_model=ResearchJobListResponse,
    summary="List recent research jobs",
    description="Returns recent async research jobs for the current workspace.",
)
async def list_jobs(
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    jobs = await list_research_jobs(db, workspace_id=current_workspace.id, limit=limit)
    return {"items": [serialize_job(job) for job in jobs]}


@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
    summary="Get a research job by id",
    description="Returns persisted status, progress, logs, and result linkage for one job.",
    responses={404: {"model": ErrorResponse, "description": "Job was not found."}},
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    job = await get_research_job(db, job_id, workspace_id=current_workspace.id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return serialize_job(job)
