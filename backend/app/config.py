from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://ada:ada@localhost:5432/ada"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    upload_dir: str = "./storage/uploads"
    sample_dir: str = "./data/samples"
    max_upload_mb: int = 25
    max_files_per_user: int = 10
    max_rows: int = 1000000
    sql_timeout_s: int = 20
    sql_row_limit: int = 10000
    llm_rows_limit: int = 40
    agent_max_iters: int = 6
    cache_ttl_s: int = 3600

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3-super-120b-a12b"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    clerk_publishable_key: str = ""
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    clerk_authorized_parties: str = ""

    embedding_model: str = "BAAI/bge-small-en-v1.5"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
