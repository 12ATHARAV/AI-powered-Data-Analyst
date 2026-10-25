from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.routes_upload import router as upload_router
from .api.routes_eda import router as eda_router
from .api.routes_dashboard import router as dashboard_router
from .api.routes_chat import router as chat_router
from .api.routes_health import router as health_router
from .api.routes_cleaning import router as cleaning_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    yield

app = FastAPI(
    title="AI-Powered Data Analyst Engine",
    description="Multi-agent data analyst backend with live observability and dual-LLM resilience.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
