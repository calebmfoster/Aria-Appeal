from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field

class ScriptGenerationRequest(BaseModel):
    """
    Schema for the script generation request.
    """
    target_audience: str = Field(..., description="The demographic or group the campaign targets.")
    cause: str = Field(..., description="The core mission or cause of the non-profit.")
    primary_emotion: str = Field(..., description="The primary emotional tone (e.g., 'Empathy', 'Urgency', 'Hope').")

class ScriptSentence(BaseModel):
    """
    Schema for a single generated sentence.
    """
    id: UUID = Field(..., description="Unique identifier for the sentence.")
    text: str = Field(..., description=" The content of the sentence.")
    duration_estimate: Optional[float] = Field(None, description="Estimated duration in seconds (optional).")
    emotion: Optional[str] = Field(None, description="TTS delivery direction, e.g. 'speak with quiet urgency'.")

class ScriptGenerationResponse(BaseModel):
    """
    Schema for the script generation response.
    """
    sentences: List[ScriptSentence] = Field(..., description="List of generated script sentences.")
