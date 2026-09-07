from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict
from uuid import UUID
from enum import Enum
from datetime import datetime

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    MASTERED = "mastered"

class ScriptSegmentBase(BaseModel):
    text: str
    sequence_order: int
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    audio_url: Optional[str] = None
    voice_profile_id: Optional[UUID] = None
    emotion: Optional[str] = None
    speaker_preset: Optional[str] = None
    pitch_shift: float = 0.0

class ScriptSegmentCreate(ScriptSegmentBase):
    pass

class ScriptSegmentUpdate(BaseModel):
    text: Optional[str] = None
    emotion: Optional[str] = None
    voice_profile_id: Optional[UUID] = None
    speaker_preset: Optional[str] = None
    pitch_shift: Optional[float] = None

class ScriptSegmentRead(ScriptSegmentBase):
    id: UUID
    project_id: UUID

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    cause: str
    target_audience: str
    primary_emotion: str
    custom_script: Optional[str] = None
    # Optional enrichment fields for richer AI generation
    organization_name: Optional[str] = None
    story_hook: Optional[str] = None
    script_length: Optional[Literal["30s", "60s", "90s"]] = "30s"
    messaging_strategy: Optional[Literal["urgency", "hope", "gratitude", "empowerment"]] = None
    ask_amount: Optional[str] = None
    # Initial voice applied to all segments. Mutually exclusive: a cloned-voice
    # UUID OR a preset speaker name. Both None → chained generation defaults to Aiden.
    voice_profile_id: Optional[str] = None
    speaker_preset: Optional[str] = None
    # "audio" (default) or "video". Persisted into target_audience["medium"];
    # the key's absence means audio, so existing campaigns are untouched.
    medium: Optional[Literal["audio", "video"]] = "audio"


class SegmentAddRequest(BaseModel):
    text: str
    sequence_order: int
    emotion: Optional[str] = None


class SegmentReorderBody(BaseModel):
    segment_ids: List[UUID]


class SegmentRewriteRequest(BaseModel):
    text: str
    prompt: str


class SegmentRewriteResponse(BaseModel):
    rewritten_text: str

class ProjectBase(BaseModel):
    title: str
    target_audience: Dict[str, Any]
    status: ProjectStatus

class ProjectRead(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: Optional[datetime] = None
    segments: List[ScriptSegmentRead] = []

    class Config:
        from_attributes = True


class ProjectSettingsUpdate(BaseModel):
    """Project-level settings the studio can change after creation."""
    medium: Optional[Literal["audio", "video"]] = None
    subtitle_style: Optional[Dict[str, Any]] = None
