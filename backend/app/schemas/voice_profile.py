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
        preview_url = None
        if profile.reference_audio_path:
            # Serve the reference audio as a preview via the static mount
            import os
            filename = os.path.basename(profile.reference_audio_path)
            preview_url = f"/static/voice_uploads/{filename}"

        return cls(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            base_model=profile.base_model,
            has_cloned_voice=profile.reference_audio_path is not None,
            preview_url=preview_url,
        )

class VoiceValidationResponse(BaseModel):
    is_valid: bool
    lufs: float
    speech_ratio: float
    errors: List[str]
