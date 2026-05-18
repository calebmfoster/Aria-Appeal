from fastapi import APIRouter, Depends, HTTPException
from app.schemas.script import ScriptGenerationRequest, ScriptGenerationResponse
from app.services.llm import LLMService
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(
    request: ScriptGenerationRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Generates a script based on the provided parameters using a local LLM.
    Requires authentication.
    """
    try:
        sentences = LLMService.generate_script(
            target_audience=request.target_audience,
            cause=request.cause,
            primary_emotion=request.primary_emotion
        )
        return ScriptGenerationResponse(sentences=sentences)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
