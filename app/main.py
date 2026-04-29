"""
FastAPI application entry point.
Configures middleware, lifespan events, exception handlers, and routers.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database.connection import create_tables, dispose_engine
from app.routes import analyze, auth, dashboard, health

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Lifespan (startup / shutdown)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs on startup and shutdown."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("  AI Resume Screener API — Starting")
    logger.info("  Provider : %s (%s)", settings.AI_PROVIDER, settings.active_model)
    logger.info("  Database : %s", settings.DATABASE_URL.split("@")[-1])  # hide credentials
    logger.info("=" * 60)

    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables created / verified.")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

    yield  # ← App runs here

    # Shutdown
    logger.info("Shutting down — disposing database engine...")
    await dispose_engine()
    logger.info("Shutdown complete.")


# ──────────────────────────────────────────────
#  App Factory
# ──────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI Resume Screener API",
        description=(
            "Production-grade REST API that analyzes resumes against job descriptions "
            "using AI (OpenAI / Anthropic). Returns match scores, missing skills, "
            "and specific rewrite suggestions."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS Middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ──
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Return clean validation errors with 422 status."""
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation failed. Check your input.",
                "error_code": "VALIDATION_ERROR",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions — never leak stack traces."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred. Please try again.",
                "error_code": "INTERNAL_ERROR",
            },
        )

    # ── Routers ──
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(analyze.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    # ── Static files ──
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ── Static routes ──
    @app.get("/", response_class=HTMLResponse, tags=["Frontend"])
    async def landing_page():
        """Serve the premium landing page."""
        return FileResponse("app/static/landing.html")

    @app.get("/home", response_class=HTMLResponse, tags=["Frontend"])
    async def home_page():
        """Redirect /home to / for a cleaner UX."""
        return RedirectResponse(url="/")

    @app.get("/results", response_class=HTMLResponse, tags=["Frontend"])
    async def results_page():
        """Serve the dedicated results dashboard."""
        return FileResponse("app/static/results.html")

    return app


# Create the app instance (used by uvicorn)
app = create_app()
