from pydantic import BaseModel
from typing import Optional

class AudioGenerationRequest(BaseModel):
    text: str
    voice_profile_id: Optional[str] = None
    emotion: Optional[str] = None

class AudioGenerationResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None

class RegenerateRequest(BaseModel):
    sentence_id: str
    text: str
    start_ms: int
    end_ms: int
    original_file_url: Optional[str] = None
    voice_profile_id: Optional[str] = None
    emotion: Optional[str] = None
