import os
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter
from ..config import settings
from ..db.engine import list_all_tables

router = APIRouter(prefix="/api", tags=["System Health"])

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Returns application status, model configs, and database stats."""
    db_path = Path(settings.DATABASE_PATH)
    db_size_bytes = db_path.stat().st_size if db_path.exists() else 0
    tables = list_all_tables()

    return {
        "status": "online",
        "service": "AI-Powered Data Analyst API",
        "database": {
            "type": "SQLite",
            "path": settings.DATABASE_PATH,
            "size_kb": round(db_size_bytes / 1024, 2),
            "table_count": len(tables),
            "tables": tables,
        },
        "models": {
            "primary": {
                "name": settings.NVIDIA_MODEL,
                "provider": "NVIDIA",
                "configured": bool(settings.NVIDIA_API_KEY),
            },
            "fallback": {
                "name": settings.GROQ_MODEL,
                "provider": "Groq",
                "configured": bool(settings.GROQ_API_KEY),
            },
        },
    }
