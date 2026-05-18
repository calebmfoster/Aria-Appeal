from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from typing import Optional
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.api.deps import limiter
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.script_segment import ScriptSegment
from app.schemas.project import ProjectCreate, ProjectRead, ScriptSegmentUpdate, ScriptSegmentRead, SegmentRewriteRequest, SegmentRewriteResponse
from app.services.llm import LLMService
from app.core.system_config import config_manager
from app.services.mastering_service import mastering_service
from app.services.tts_engine import tts_service
import uuid
import os
import asyncer
from app.worker import generate_audio_task
from app.db.session import SessionLocal
from app.models.voice_profile import VoiceProfile

def _get_wav_duration_ms(audio_url: str) -> int:
    """Get the duration of a WAV file in milliseconds from its static URL."""
    import soundfile as sf
    filename = audio_url.split("/")[-1]
    local_path = os.path.join(tts_service.output_dir, filename)
    try:
        info = sf.info(local_path)
        return int(info.duration * 1000)
    except Exception:
        return 0


def _extract_audio_tail(audio_url: str, tail_seconds: float = 2.0) -> Optional[str]:
    """Extract the last N seconds of a generated WAV and write to a temp file.
    Returns the temp file path, or None on failure."""
    import soundfile as sf
    import numpy as np
    import tempfile
    filename = audio_url.split("/")[-1]
    local_path = os.path.join(tts_service.output_dir, filename)
    try:
        data, sr = sf.read(local_path)
        tail_samples = int(tail_seconds * sr)
        tail = data[-tail_samples:] if len(data) > tail_samples else data
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, dir=tts_service.output_dir, prefix="chain_"
        )
        sf.write(tmp.name, tail, sr)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"Could not extract audio tail from {filename}: {e}")
        return None


async def _generate_baseline_audio_for_project(project_id: uuid.UUID):
    async with SessionLocal() as db:
        stmt = select(Project).where(Project.id == project_id).options(selectinload(Project.segments))
        result = await db.execute(stmt)
        project = result.scalars().first()
        if not project:
            return

        project.segments.sort(key=lambda s: s.sequence_order)
        project_emotion = project.target_audience.get("emotion") if project.target_audience else None

        # Tail of the last clone-path segment, used to chain prosody into the next segment
        prev_clone_tail: Optional[str] = None

        for i, segment in enumerate(project.segments):
            if not segment.audio_url:
                try:
                    speaker_name = None
                    ref_audio_path = None
                    ref_text = None
                    is_clone_path = False

                    # speaker_preset takes priority over voice_profile_id for preset speakers
                    if segment.speaker_preset:
                        speaker_name = segment.speaker_preset
                    elif segment.voice_profile_id:
                        stmt_vp = select(VoiceProfile).where(VoiceProfile.id == segment.voice_profile_id)
                        res_vp = await db.execute(stmt_vp)
                        profile = res_vp.scalars().first()
                        if profile:
                            speaker_name = profile.name
                            is_clone_path = True
                            if i > 0 and prev_clone_tail:
                                ref_audio_path = prev_clone_tail
                                ref_text = None
                            else:
                                ref_audio_path = profile.reference_audio_path
                                ref_text = profile.reference_text

                    # Per-segment emotion; fall back to project-level
                    emotion = segment.emotion or project_emotion
                    # For preset-speaker segments after the first, hint continuity via instruct
                    if i > 0 and emotion and not is_clone_path:
                        emotion = f"continuing the emotional arc, {emotion}"

                    pitch = segment.pitch_shift or 0.0

                    audio_url = await asyncer.asyncify(generate_audio_task)(
                        text=segment.text,
                        voice_profile_id=speaker_name,
                        emotion=emotion,
                        reference_audio_path=ref_audio_path,
                        reference_text=ref_text,
                        pitch_shift=pitch,
                    )
                    segment.audio_url = audio_url
                    await db.commit()

                    # Save tail for next segment if we're on the clone path
                    if is_clone_path:
                        prev_clone_tail = _extract_audio_tail(audio_url)
                    else:
                        prev_clone_tail = None

                except Exception as e:
                    print(f"Failed to generate baseline async for segment {segment.id}: {e}")
                    prev_clone_tail = None

        # Recalculate cumulative timestamps from audio durations
        await _recalculate_segment_timestamps(db, project)

async def _recalculate_segment_timestamps(db: AsyncSession, project):
    """Recalculate cumulative start/end timestamps from audio file durations."""
    project.segments.sort(key=lambda s: s.sequence_order)
    cursor_ms = 0
    for seg in project.segments:
        seg.start_time_ms = cursor_ms
        if seg.audio_url:
            duration = _get_wav_duration_ms(seg.audio_url)
            seg.end_time_ms = cursor_ms + duration
            cursor_ms += duration
        else:
            seg.end_time_ms = cursor_ms
    await db.commit()


router = APIRouter()

@router.post("", response_model=ProjectRead)
@limiter.limit("5/minute")
async def create_project(
    request: Request,
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new project and generate script segments.
    """
    # 1. Create Project
    project_title = project_in.organization_name or project_in.cause
    new_project = Project(
        user_id=current_user.id,
        title=project_title,
        target_audience={
            "audience": project_in.target_audience,
            "emotion": project_in.primary_emotion,
            "cause": project_in.cause,
            "organization_name": project_in.organization_name,
            "script_length": project_in.script_length,
            "messaging_strategy": project_in.messaging_strategy,
        },
        status=ProjectStatus.GENERATED
    )
    db.add(new_project)
    await db.flush() # flush to generate new_project.id

    # 2. Generate Script (LLM or custom)
    if project_in.custom_script and project_in.custom_script.strip():
        # User provided their own script — split into segments
        import re
        raw = project_in.custom_script.strip()
        # Split on double newlines (paragraphs) first; fall back to sentences
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
        if len(paragraphs) >= 2:
            segment_texts = paragraphs
        else:
            # Split by sentence boundaries
            segment_texts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if s.strip()]
            if not segment_texts:
                segment_texts = [raw]
    else:
        try:
            sentences = await asyncer.asyncify(LLMService.generate_script)(
                target_audience=project_in.target_audience,
                cause=project_in.cause,
                primary_emotion=project_in.primary_emotion,
                organization_name=project_in.organization_name,
                story_hook=project_in.story_hook,
                script_length=project_in.script_length or "30s",
                messaging_strategy=project_in.messaging_strategy,
                ask_amount=project_in.ask_amount,
            )
            segment_texts = [(s.text, s.emotion) for s in sentences]
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    # 3. Create Script Segments
    for i, item in enumerate(segment_texts):
        text, emotion = item if isinstance(item, tuple) else (item, None)
        segment = ScriptSegment(
            project_id=new_project.id,
            text=text,
            emotion=emotion,
            sequence_order=i,
        )
        db.add(segment)
    
    await db.commit()
    
    background_tasks.add_task(_generate_baseline_audio_for_project, new_project.id)
    
    # 4. Fetch the created project with segments
    stmt = select(Project).where(Project.id == new_project.id).options(selectinload(Project.segments))
    result = await db.execute(stmt)
    project_with_segments = result.scalars().first()
    
    return project_with_segments


@router.post("/rewrite-segment", response_model=SegmentRewriteResponse)
@limiter.limit("10/minute")
async def rewrite_segment(
    request: Request,
    body: SegmentRewriteRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Use the LLM to rewrite a segment based on a user prompt.
    E.g. "make it more urgent", "shorten to two sentences"
    """
    rewrite_prompt = f"""You are a copywriter editing a non-profit fundraising script segment.

CURRENT TEXT:
"{body.text}"

USER INSTRUCTION:
{body.prompt}

Rewrite the text following the user's instruction. Return ONLY the rewritten text, no quotes, no explanations, no markdown."""

    settings = config_manager.get_settings()

    try:
        if settings.llm_provider == "claude":
            import anthropic, os
            api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise RuntimeError("Anthropic API key not configured.")
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=512,
                system="You are a concise copywriter. Return only the rewritten text.",
                messages=[{"role": "user", "content": rewrite_prompt}],
            )
            content = response.content[0].text.strip()
        else:
            generator = LLMService._get_pipeline()
            messages = [
                {"role": "system", "content": "You are a concise copywriter. Return only the rewritten text."},
                {"role": "user", "content": rewrite_prompt}
            ]
            prompt_text = generator.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            outputs = generator(prompt_text, max_new_tokens=256, temperature=0.7, do_sample=True)
            content = outputs[0]["generated_text"].split("<|im_start|>assistant\n")[-1].strip()

        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        return SegmentRewriteResponse(rewritten_text=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    List all projects for the current user.
    """
    stmt = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .options(selectinload(Project.segments))
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().unique().all()
    return projects

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get a specific project by ID.
    """
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.segments))
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Sort segments by sequence_order before returning
    project.segments.sort(key=lambda s: s.sequence_order)
    return project

@router.post("/{project_id}/export")
async def export_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Exports a project by stitching all segment audio files using the mastering service.
    """
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.segments))
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.segments.sort(key=lambda s: s.sequence_order)

    segment_paths = []
    for segment in project.segments:
        if not segment.audio_url:
            raise HTTPException(
                status_code=400, 
                detail=f"Segment {segment.sequence_order} is missing audio. Generate all segments before exporting."
            )
        filename = segment.audio_url.split("/")[-1]
        local_path = os.path.join(tts_service.output_dir, filename)
        if not os.path.exists(local_path):
            raise HTTPException(
                status_code=400,
                detail=f"Audio file for segment {segment.sequence_order} not found on disk."
            )
        segment_paths.append(local_path)

    # Master the project
    mastered_filename = f"master_{project_id}.wav"
    output_path = os.path.join(tts_service.output_dir, mastered_filename)
    
    try:
        mastering_service.master_project(segment_paths, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mastering failed: {str(e)}")

    master_audio_url = f"/static/audio/{mastered_filename}"
    
    project.status = ProjectStatus.MASTERED
    await db.commit()
    
    return {"message": "Project exported successfully", "master_audio_url": master_audio_url}


@router.patch("/{project_id}/segments/{segment_id}", response_model=ScriptSegmentRead)
async def update_segment(
    project_id: uuid.UUID,
    segment_id: uuid.UUID,
    segment_in: ScriptSegmentUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Update a segment's text, emotion, or voice_profile_id without triggering audio regeneration.
    """
    # Verify project ownership
    stmt = select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch segment
    stmt = select(ScriptSegment).where(ScriptSegment.id == segment_id, ScriptSegment.project_id == project_id)
    result = await db.execute(stmt)
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Apply updates
    update_data = segment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.commit()
    await db.refresh(segment)
    return segment


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Delete a project and all its segments.
    """
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.segments))
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete segment audio files
    for segment in project.segments:
        if segment.audio_url:
            filename = segment.audio_url.split("/")[-1]
            local_path = os.path.join(tts_service.output_dir, filename)
            if os.path.exists(local_path):
                os.remove(local_path)
        await db.delete(segment)

    # Delete master audio if exists
    master_path = os.path.join(tts_service.output_dir, f"master_{project_id}.wav")
    if os.path.exists(master_path):
        os.remove(master_path)

    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}

