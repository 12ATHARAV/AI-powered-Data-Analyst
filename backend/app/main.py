import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db.engine import cleanup_expired_sessions
from .api.middleware_session import SessionAndRateLimitMiddleware
from .api.routes_upload import router as upload_router
from .api.routes_eda import router as eda_router
from .api.routes_dashboard import router as dashboard_router
from .api.routes_chat import router as chat_router
from .api.routes_health import router as health_router
from .api.routes_cleaning import router as cleaning_router

async def _session_reaper_task():
    """Background task running every 30 minutes to clean up stale demo sessions."""
    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutes
            cleanup_expired_sessions(max_age_hours=4)
        except asyncio.CancelledError:
            break
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    cleanup_expired_sessions(max_age_hours=4)
    reaper = asyncio.create_task(_session_reaper_task())
    try:
        yield
    finally:
        reaper.cancel()

app = FastAPI(
    title="AI-Powered Data Analyst Engine",
    description="Multi-agent data analyst backend with live observability, dual-LLM resilience, and multi-tenant session isolation.",
    version="2.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-ID"],
)

# Multi-tenant Session Isolation & Rate Limiting Middleware
app.add_middleware(SessionAndRateLimitMiddleware)

# Register Routers
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(eda_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(cleaning_router)

@app.get("/")
def root():
    return {
        "app": "AI-Powered Data Analyst",
        "version": "2.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
