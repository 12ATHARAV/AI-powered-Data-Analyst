from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings

router = APIRouter(tags=["health"])


def _check_postgres(db_url: str) -> bool:
    try:
        from sqlalchemy import create_engine
        engine = create_engine(db_url, connect_args={"connect_timeout": 2} if "psycopg" in db_url else {})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis(redis_url: str) -> bool:
    try:
        import redis
        client = redis.Redis.from_url(redis_url, socket_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


def _check_qdrant(qdrant_url: str) -> bool:
    try:
        if qdrant_url == ":memory:":
            return True
        import httpx
        resp = httpx.get(f"{qdrant_url.rstrip('/')}/healthz", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


@router.get("/health")
def health_check() -> dict:
    """Return health status of core dependencies without exposing secrets."""
    settings = get_settings()
    pg_ok = _check_postgres(settings.database_url)
    redis_ok = _check_redis(settings.redis_url)
    qdrant_ok = _check_qdrant(settings.qdrant_url)
    nvidia_configured = bool(settings.nvidia_api_key.strip())
    groq_configured = bool(settings.groq_api_key.strip())

    return {
        "status": "ok",
        "postgres": pg_ok,
        "redis": redis_ok,
        "qdrant": qdrant_ok,
        "llm": {
            "nvidia": nvidia_configured,
            "groq": groq_configured,
        },
    }
