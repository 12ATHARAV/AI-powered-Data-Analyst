import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Primary LLM
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"

    # Fallback LLM
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # Server & Storage
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173
    DATABASE_PATH: str = str(BASE_DIR / "storage" / "analyst.db")
    UPLOAD_DIR: str = str(BASE_DIR / "storage" / "uploads")
    SAMPLE_DIR: str = str(BASE_DIR / "data" / "samples")

    def ensure_dirs(self) -> None:
        Path(self.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

settings = Settings()

def _resolve_from_root(p: str) -> str:
    path = Path(p)
    if path.is_absolute():
        return str(path)
    return str(BASE_DIR / path)

# .env uses root-relative paths; anchor them so the app behaves the same
# no matter which directory uvicorn is launched from.
settings.DATABASE_PATH = _resolve_from_root(settings.DATABASE_PATH)
settings.UPLOAD_DIR = _resolve_from_root(settings.UPLOAD_DIR)
settings.SAMPLE_DIR = _resolve_from_root(settings.SAMPLE_DIR)

settings.ensure_dirs()
