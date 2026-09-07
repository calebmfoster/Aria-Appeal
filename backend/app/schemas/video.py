import uuid
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


class VideoClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    segment_id: Optional[uuid.UUID] = None
    sequence_order: int
    source_type: Literal["generated", "asset", "uploaded"]
    status: Literal["pending", "generating", "ready", "failed"]
    prompt: Optional[str] = None
    video_url: Optional[str] = None
    duration_ms: Optional[int] = None
    trim_start_ms: Optional[int] = None
    trim_end_ms: Optional[int] = None
    timeline_start_ms: Optional[int] = None
    timeline_end_ms: Optional[int] = None


class VideoClipUpdate(BaseModel):
    """Partial update for editor edits (prompt, trim, ordering)."""
    prompt: Optional[str] = None
    trim_start_ms: Optional[int] = None
    trim_end_ms: Optional[int] = None
    sequence_order: Optional[int] = None


class VideoBrief(BaseModel):
    """Campaign-level visual direction stored in Project.video_brief."""
    style_prompt: Optional[str] = None
    character_sheet: Optional[str] = None
    video_master_url: Optional[str] = None


class SubtitleStyle(BaseModel):
    """Stored in Project.subtitle_style; controls ASS burn-in."""
    enabled: bool = True
    font_size: int = 36
    position: Literal["bottom", "top", "center"] = "bottom"
    color: str = "FFFFFF"


class VideoClipsResponse(BaseModel):
    """Everything the studio's Video tab needs in one read."""
    clips: list[VideoClipRead] = []
    video_brief: Optional[dict] = None
    subtitle_style: Optional[dict] = None
