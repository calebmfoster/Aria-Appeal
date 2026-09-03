from pydantic import BaseModel
from typing import Optional, List
import uuid

class VoiceProfileBase(BaseModel):
    name: str
    base_model: Optional[str] = "Qwen3-TTS-12Hz-1.7B-Base"

class VoiceProfileCreate(VoiceProfileBase):
    pass

class VoiceProfileUpdate(VoiceProfileBase):
    name: Optional[str] = None

class VoiceProfileRename(BaseModel):
    name: str

class VoiceProfileResponse(VoiceProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    has_cloned_voice: bool = False
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_clone_status(cls, profile):
        # Point at the synthesized greeting cache, NOT the user's raw uploaded
        # reference clip — previewing that played back their whole recording.
        # None until the preview exists; POST /{id}/preview creates it.
        from app.services import voice_preview

        return cls(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            base_model=profile.base_model,
            has_cloned_voice=profile.reference_audio_path is not None,
            preview_url=voice_preview.clone_preview_url(profile.id),
        )

class VoiceValidationResponse(BaseModel):
    is_valid: bool
    lufs: float
    speech_ratio: float
    errors: List[str]


class VoicePresetResponse(BaseModel):
    speaker: str
    label: str
    language: str
    language_label: str
    gender: str
    accent: Optional[str] = None
    greeting: str
    gloss: str
    preview_url: Optional[str] = None


class VoicePreviewResponse(BaseModel):
    preview_url: str
