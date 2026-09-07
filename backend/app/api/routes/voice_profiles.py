from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import logging
from app.db.session import get_db
from app.schemas.voice_profile import (
    VoiceProfileCreate, VoiceProfileResponse, VoiceProfileRename,
    VoiceValidationResponse, VoicePresetResponse, VoicePreviewResponse,
)
from app.models.voice_profile import VoiceProfile
from app.services.voice_validator import voice_validator
from app.services.voice_cloner import voice_cloner
from app.services import voice_preview
from app.services.voice_presets import PRESETS, get_preset
from app.api import deps
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=VoiceProfileResponse)
async def create_voice_profile(
    name: str = Form(...),
    base_model: str = Form("Qwen3-TTS-12Hz-1.7B-Base"),
    reference_text: Optional[str] = Form(None),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Uploads a voice profile, validates the audio, extracts acoustic embeddings
    via the Qwen3-TTS tokenizer, and saves the profile for zero-shot cloning.
    """
    audio_data = await file.read()

    # Validate audio quality (LUFS + VAD)
    validation = voice_validator.validate_audio(audio_data)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Audio validation failed", "errors": validation["errors"]}
        )

    # Save reference audio to disk for zero-shot cloning
    reference_audio_path = voice_cloner.save_reference_audio(audio_data, name)
    logger.info(f"Reference audio saved: {reference_audio_path}")

    # Extract real acoustic embeddings from the reference audio
    embedding = voice_cloner.extract_embedding(audio_data)
    logger.info(f"Extracted embedding for '{name}' (non-zero: {sum(1 for v in embedding if v != 0.0)}/{len(embedding)})")

    db_voice = VoiceProfile(
        name=name,
        base_model=base_model,
        user_id=current_user.id,
        embedding=embedding,
        reference_audio_path=reference_audio_path,
        reference_text=reference_text,
    )
    db.add(db_voice)
    await db.commit()
    await db.refresh(db_voice)

    # Warm the greeting preview so the dashboard usually has one by the time the
    # list refreshes; the POST /{id}/preview route regenerates it lazily otherwise.
    if background_tasks is not None:
        background_tasks.add_task(
            voice_preview.ensure_clone_preview,
            db_voice.id, db_voice.reference_audio_path, db_voice.reference_text,
        )

    return VoiceProfileResponse.from_orm_with_clone_status(db_voice)

@router.get("/", response_model=List[VoiceProfileResponse])
async def list_voice_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Lists all voice profiles for the current user.
    """
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.user_id == current_user.id))
    profiles = result.scalars().all()
    return [VoiceProfileResponse.from_orm_with_clone_status(p) for p in profiles]

@router.get("/presets", response_model=List[VoicePresetResponse])
async def list_voice_presets():
    """The nine Qwen preset speakers with their native languages.

    Reads the cache only — never synthesizes, so the pickers stay instant.
    """
    return [
        VoicePresetResponse(
            speaker=p.speaker,
            label=p.label,
            language=p.language,
            language_label=p.language_label,
            gender=p.gender,
            accent=p.accent,
            greeting=p.greeting,
            gloss=p.gloss,
            preview_url=voice_preview.cached_url(
                voice_preview.preset_preview_filename(p.speaker)
            ),
        )
        for p in PRESETS
    ]


@router.post("/presets/{speaker}/preview", response_model=VoicePreviewResponse)
async def generate_preset_preview(speaker: str):
    """Synthesize (or return the cached) greeting for a preset, in its own language."""
    if get_preset(speaker) is None:
        raise HTTPException(status_code=404, detail=f"Unknown preset speaker: {speaker}")

    url = await voice_preview.ensure_preset_preview(speaker)
    if not url:
        raise HTTPException(status_code=503, detail="Preview synthesis is unavailable.")
    return VoicePreviewResponse(preview_url=url)


@router.post("/{profile_id}/preview", response_model=VoicePreviewResponse)
async def generate_clone_preview(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Synthesize (or return the cached) greeting in a cloned voice."""
    result = await db.execute(select(VoiceProfile).where(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == current_user.id,
    ))
    profile = result.scalars().first()
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    url = await voice_preview.ensure_clone_preview(
        profile.id, profile.reference_audio_path, profile.reference_text
    )
    if not url:
        raise HTTPException(status_code=503, detail="Preview synthesis is unavailable.")
    return VoicePreviewResponse(preview_url=url)


@router.delete("/{profile_id}")
async def delete_voice_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Deletes a voice profile.
    """
    result = await db.execute(select(VoiceProfile).where(
        VoiceProfile.id == profile_id, 
        VoiceProfile.user_id == current_user.id
    ))
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    
    await db.delete(profile)
    await db.commit()
    voice_preview.delete_clone_preview(profile_id)
    return {"message": "Voice profile deleted"}

@router.patch("/{profile_id}", response_model=VoiceProfileResponse)
async def rename_voice_profile(
    profile_id: uuid.UUID,
    body: VoiceProfileRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(VoiceProfile).where(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == current_user.id
    ))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    profile.name = body.name
    await db.commit()
    await db.refresh(profile)

    return VoiceProfileResponse.from_orm_with_clone_status(profile)

@router.post("/validate", response_model=VoiceValidationResponse)
async def validate_voice_audio(
    file: UploadFile = File(...)
):
    """
    Validates audio without saving (for real-time feedback).
    """
    audio_data = await file.read()
    validation = voice_validator.validate_audio(audio_data)
    return validation
