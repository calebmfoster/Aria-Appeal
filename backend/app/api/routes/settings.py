from fastapi import APIRouter, HTTPException
from app.core.system_config import config_manager, SystemSettings

router = APIRouter()

@router.get("/settings", response_model=SystemSettings)
async def get_settings():
    """
    Retrieve current system settings.
    """
    try:
        settings = config_manager.get_settings()
        if not settings:
             # Should be initialized by ConfigManager on startup
            raise HTTPException(status_code=500, detail="Settings not initialized")
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings", response_model=SystemSettings)
async def update_settings(settings: SystemSettings):
    """
    Update system settings.
    """
    try:
        config_manager.update_settings(settings)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
