from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup: Eager-load TTS models ===
    from app.services.tts_engine import tts_service
    logger.info("Pre-loading TTS models on startup...")
    tts_service._ensure_initialized()
    if tts_service.mode == "mock":
        logger.warning("TTS is running in MOCK mode (models failed to load). Audio will be sine wave beeps.")
    else:
        preset_ok = tts_service.preset_model is not None
        clone_ok = tts_service.clone_model is not None
        logger.info(f"TTS ready — preset model: {'loaded' if preset_ok else 'FAILED'}, clone model: {'loaded' if clone_ok else 'FAILED'}")
    yield
    # === Shutdown ===
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.deps import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Import all models to ensure SQLAlchemy mapper is initialized correctly
from app.db import base as _  # noqa: F401

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Fallback/Default for development — allow all local origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

import os
from fastapi.staticfiles import StaticFiles

@app.get("/health")
def health_check():
    from app.services.tts_engine import tts_service
    return {
        "status": "ok",
        "version": "0.1.0",
        "tts_mode": tts_service.mode,
        "tts_initialized": tts_service._initialized,
        "preset_model_loaded": tts_service.preset_model is not None,
        "clone_model_loaded": tts_service.clone_model is not None,
        "device": tts_service.device,
    }

# Mount static directory for serving audio files with CORS
# When STATIC_AUDIO_DIR is set (worktree launch), serve from its parent so
# /static/audio/... resolves to the main repo's audio files.
if settings.STATIC_AUDIO_DIR:
    static_dir = os.path.dirname(settings.STATIC_AUDIO_DIR)
else:
    static_dir = os.path.join(os.getcwd(), "static")
os.makedirs(static_dir, exist_ok=True)

static_app = FastAPI()
static_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
static_app.mount("/", StaticFiles(directory=static_dir), name="static")
app.mount("/static", static_app)

from app.api.routes import generation, settings as settings_router, audio, auth, voice_profiles, projects
app.include_router(generation.router, prefix=settings.API_V1_STR, tags=["generation"])
app.include_router(settings_router.router, prefix=settings.API_V1_STR, tags=["settings"])
app.include_router(audio.router, prefix=settings.API_V1_STR, tags=["audio"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(voice_profiles.router, prefix=f"{settings.API_V1_STR}/voice-profiles", tags=["voice-profiles"])
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}/projects", tags=["projects"])
