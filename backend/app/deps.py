from typing import Any

from app.auth.clerk import get_current_user
from app.db.session import get_session

# Canonical dependencies for FastAPI dependency overrides
get_db = get_session


def get_cache() -> Any:
    from app.services.cache import get_cache as _get_cache
    return _get_cache()


def get_vector_store() -> Any:
    from app.services.vector import get_vector_store as _get_vector_store
    return _get_vector_store()


def get_engine_cache() -> Any:
    from app.services.engine import get_engine_cache as _get_engine_cache
    return _get_engine_cache()


def get_llm_router() -> Any:
    from app.llm.router import get_llm_router as _get_llm_router
    return _get_llm_router()


__all__ = [
    "get_db",
    "get_current_user",
    "get_cache",
    "get_vector_store",
    "get_engine_cache",
    "get_llm_router",
]
