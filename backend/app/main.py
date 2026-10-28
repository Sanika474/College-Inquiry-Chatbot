"""CampusIQ FastAPI Application Main Entrypoint."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("campusiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Initializing %s in %s mode...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    logger.info("CORS Allowed Origins: %s", settings.CORS_ORIGINS)
    logger.info("AI Provider Fallback: %s", settings.AI_PROVIDER or "Disabled (Rule-Engine Only)")
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack college inquiry chatbot and academic information assistant API.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "campusiq-backend",
        "version": "1.0.0",
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def api_v1_health():
    """Detailed versioned health check endpoint."""
    return {
        "status": "healthy",
        "service": "campusiq-backend",
        "environment": settings.ENVIRONMENT,
        "api_version": "v1",
        "ai_fallback_enabled": bool(settings.AI_PROVIDER and settings.AI_API_KEY),
        "ai_provider": settings.AI_PROVIDER or "none (rule_engine_only)",
    }


# Mount Versioned API Routes
from app.api.v1.router import api_v1_router

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Mount Static Assets & Frontend Pages
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

assets_dir = os.path.join(workspace_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

images_dir = os.path.join(workspace_dir, "images")
if os.path.exists(images_dir):
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

sounds_dir = os.path.join(workspace_dir, "sounds")
if os.path.exists(sounds_dir):
    app.mount("/sounds", StaticFiles(directory=sounds_dir), name="sounds")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve index.html at root."""
    index_path = os.path.join(workspace_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CampusIQ API"}


@app.get("/{page_name}.html", include_in_schema=False)
async def serve_html_page(page_name: str):
    """Serve specific HTML pages."""
    page_path = os.path.join(workspace_dir, f"{page_name}.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse(status_code=404, content={"detail": f"Page {page_name}.html not found"})


