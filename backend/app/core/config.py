from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Aria Appeal Backend"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    TTS_MODE: str = "qwen-local"
    STATIC_AUDIO_DIR: str = ""  # absolute path override; defaults to cwd/static/audio
    QWEN_MODEL_PATH: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    BACKEND_CORS_ORIGINS: list[str] = []
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
