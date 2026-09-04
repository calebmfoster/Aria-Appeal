import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User
from app.models.video_clip import VideoClipStatus
from app.schemas.video import VideoClipsResponse
from app.services.video.assembly import assemble_project, source_fingerprint

logger = logging.getLogger(__name__)

router = APIRouter()

STATUS_KEY = "video_export_status"
URL_KEY = "video_master_url"
ERROR_KEY = "video_export_error"
FINGERPRINT_KEY = "video_source_fingerprint"


async def _set_export_state(db, project, status, url=None, error=None):
    """video_brief is a JSON column, so replace the dict — mutating it in place
    does not mark the attribute dirty and the write would be silently dropped."""
    brief = dict(project.video_brief or {})
    brief[STATUS_KEY] = status
    if url is not None:
        brief[URL_KEY] = url
    if error is not None:
        brief[ERROR_KEY] = error
    elif status != "failed":
        brief.pop(ERROR_KEY, None)
    project.video_brief = brief
    await db.commit()


async def _run_assembly(project_id: uuid.UUID) -> None:
    """Background worker: own session, because the request's is gone by now."""
    async with SessionLocal() as db:
        project = (await db.execute(
            select(Project).where(Project.id == project_id)
        )).scalars().first()
        if project is None:
            return
        try:
            url = await assemble_project(db, project_id)
            await db.refresh(project)
            await _set_export_state(db, project, "ready", url=url)
        except Exception as exc:
            logger.exception("Video assembly failed for %s", project_id)
            await db.rollback()
            project = (await db.execute(
                select(Project).where(Project.id == project_id)
            )).scalars().first()
            if project is not None:
                await _set_export_state(db, project, "failed", error=str(exc))


def _schedule_assembly(background_tasks: BackgroundTasks, project_id: uuid.UUID) -> None:
    """Seam for tests — patched so the route can be exercised without ffmpeg.

    Uses FastAPI's BackgroundTasks rather than asyncio.create_task: a bare task
    holds no strong reference and can be collected mid-assembly.
    """
    background_tasks.add_task(_run_assembly, project_id)


async def _get_owned_project(db: AsyncSession, project_id: uuid.UUID, user: User) -> Project:
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.user_id == user.id)
        .options(selectinload(Project.video_clips), selectinload(Project.segments))
    )
    project = (await db.execute(stmt)).scalars().first()
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/video/clips", response_model=VideoClipsResponse)
async def list_video_clips(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Clips in running order, plus the project-level visual direction."""
    project = await _get_owned_project(db, project_id, current_user)
    clips = sorted(project.video_clips or [], key=lambda c: c.sequence_order)
    return VideoClipsResponse(
        clips=clips,
        video_brief=project.video_brief,
        subtitle_style=project.subtitle_style,
    )


@router.post("/{project_id}/video/export")
async def export_video(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Assemble the animatic in the background; poll the GET for progress."""
    project = await _get_owned_project(db, project_id, current_user)

    clips = list(project.video_clips or [])
    if not clips:
        raise HTTPException(status_code=400, detail="This campaign has no video clips yet.")

    unready = [c for c in clips if c.status != VideoClipStatus.READY]
    if unready:
        orders = ", ".join(str(c.sequence_order + 1) for c in sorted(unready, key=lambda c: c.sequence_order))
        raise HTTPException(
            status_code=400,
            detail=f"Clips not ready: scene {orders}. Generate or upload them before exporting.",
        )

    await _set_export_state(db, project, "running")
    _schedule_assembly(background_tasks, project_id)
    return {"status": "running", "message": "Assembly started."}


@router.get("/{project_id}/video/export")
async def export_video_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    project = await _get_owned_project(db, project_id, current_user)
    brief = project.video_brief or {}
    stored = brief.get(FINGERPRINT_KEY)
    current = source_fingerprint(project.segments or [], project.subtitle_style)
    return {
        "status": brief.get(STATUS_KEY, "idle"),
        "video_master_url": brief.get(URL_KEY),
        "error": brief.get(ERROR_KEY),
        # The script or narration changed since this animatic was built. Unlike the
        # audio master, the video does not rebuild itself — nothing else would tell
        # the user the video they are looking at is out of date.
        "stale": bool(brief.get(URL_KEY)) and stored is not None and stored != current,
    }
