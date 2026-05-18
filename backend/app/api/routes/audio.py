from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api import deps
from app.models.user import User
from app.models.script_segment import ScriptSegment
from app.db.session import SessionLocal
from app.schemas.audio import AudioGenerationRequest, AudioGenerationResponse
from app.worker import generate_audio_task, regenerate_audio_task
import uuid
import asyncer
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task status tracker for background tasks
task_statuses = {}


async def _resolve_voice_profile(voice_profile_id: str):
    """
    Look up a VoiceProfile by ID and return (speaker_name, reference_audio_path, reference_text).
    If the profile has a reference audio file, it's a cloned voice.
    Otherwise, fall back to using the profile name as a preset speaker string.
    If voice_profile_id is not a valid UUID, treat it as a preset speaker name directly.
    """
    if not voice_profile_id:
        return None, None, None

    # If it's not a valid UUID, treat it as a preset speaker name
    try:
        uuid.UUID(str(voice_profile_id))
    except ValueError:
        logger.info(f"Non-UUID voice_profile_id '{voice_profile_id}' — treating as preset speaker name")
        return voice_profile_id, None, None

    from app.models.voice_profile import VoiceProfile

    async with SessionLocal() as db:
        stmt = select(VoiceProfile).where(VoiceProfile.id == voice_profile_id)
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile:
            logger.warning(f"Voice profile '{voice_profile_id}' not found in DB — treating as preset")
            return voice_profile_id, None, None

        if profile.reference_audio_path:
            # This is a cloned voice — use reference audio for zero-shot synthesis
            logger.info(f"Resolved cloned voice profile: '{profile.name}'")
            return profile.name, profile.reference_audio_path, profile.reference_text
        else:
            # Legacy profile without reference audio — use name as preset speaker
            logger.info(f"Resolved preset voice profile: '{profile.name}'")
            return profile.name, None, None


async def _run_generate_sync(task_id: str, text: str, voice_profile_id: str, emotion: str):
    try:
        task_statuses[task_id] = {"status": "RUNNING"}

        speaker_name, ref_audio_path, ref_text = await _resolve_voice_profile(voice_profile_id)

        result = await asyncer.asyncify(generate_audio_task)(
            text=text,
            voice_profile_id=speaker_name,
            emotion=emotion,
            reference_audio_path=ref_audio_path,
            reference_text=ref_text,
        )
        task_statuses[task_id] = {"status": "SUCCESS", "result": result}
    except Exception as e:
        print(f"[{task_id}] Error in background generate_audio: {e}")
        task_statuses[task_id] = {"status": "FAILURE", "error": str(e)}


@router.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest, background_tasks: BackgroundTasks):
    """
    Triggers an asynchronous task to generate audio from text.
    """
    try:
        task_id = str(uuid.uuid4())
        task_statuses[task_id] = {"status": "PENDING"}

        background_tasks.add_task(
            _run_generate_sync,
            task_id, request.text, request.voice_profile_id, request.emotion
        )
        return AudioGenerationResponse(task_id=task_id, status="PENDING")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate-audio/{task_id}", response_model=AudioGenerationResponse)
async def get_audio_status(task_id: str):
    """
    Checks the status of the audio generation task.
    """
    try:
        task = task_statuses.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        status = task.get("status")
        result = task.get("result") if status == "SUCCESS" else None

        return AudioGenerationResponse(task_id=task_id, status=status, result=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from app.schemas.audio import RegenerateRequest


async def _run_regenerate_sync(
    task_id: str, original_file_url: str, text: str, start_ms: int, end_ms: int,
    voice_profile_id: str, emotion: str, segment_id: str
):
    try:
        task_statuses[task_id] = {"status": "RUNNING"}

        logger.info(f"[Regenerate {task_id}] Text: '{text[:80]}...'")
        logger.info(f"[Regenerate {task_id}] Emotion: '{emotion}' | Voice: '{voice_profile_id}'")

        import app.worker as worker_module

        speaker_name, ref_audio_path, ref_text = await _resolve_voice_profile(voice_profile_id)

        result = await asyncer.asyncify(worker_module.regenerate_audio_task)(
            master_file_url=original_file_url,
            new_text=text,
            start_ms=start_ms,
            end_ms=end_ms,
            voice_profile_id=speaker_name,
            emotion=emotion,
            reference_audio_path=ref_audio_path,
            reference_text=ref_text,
        )
        task_statuses[task_id] = {"status": "SUCCESS", "result": result}

        async with SessionLocal() as db:
            stmt = select(ScriptSegment).where(ScriptSegment.id == segment_id)
            res = await db.execute(stmt)
            seg = res.scalars().first()
            if seg:
                seg.audio_url = result
                await db.commit()

                # Recalculate timestamps for all segments in this project
                from sqlalchemy.orm import selectinload
                from app.models.project import Project
                from app.api.routes.projects import _recalculate_segment_timestamps
                stmt_proj = select(Project).where(Project.id == seg.project_id).options(selectinload(Project.segments))
                res_proj = await db.execute(stmt_proj)
                project = res_proj.scalars().first()
                if project:
                    await _recalculate_segment_timestamps(db, project)
    except Exception as e:
        print(f"[{task_id}] Error in background regenerate_audio: {e}")
        task_statuses[task_id] = {"status": "FAILURE", "error": str(e)}


@router.post("/regenerate-segment", response_model=AudioGenerationResponse)
async def regenerate_segment(
    request: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Triggers an asynchronous task to regenerate a segment of audio and splice it.
    """
    try:
        # 1. Synchronous update of DB with text/emotion changes
        stmt = select(ScriptSegment).where(ScriptSegment.id == request.sentence_id)
        res = await db.execute(stmt)
        seg = res.scalars().first()
        if seg:
            seg.text = request.text
            seg.emotion = request.emotion
            if request.voice_profile_id:
                seg.voice_profile_id = request.voice_profile_id
            await db.commit()

        task_id = str(uuid.uuid4())
        task_statuses[task_id] = {"status": "PENDING"}

        background_tasks.add_task(
            _run_regenerate_sync,
            task_id, request.original_file_url, request.text, request.start_ms, request.end_ms,
            request.voice_profile_id, request.emotion, request.sentence_id
        )
        return AudioGenerationResponse(task_id=task_id, status="PENDING")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
