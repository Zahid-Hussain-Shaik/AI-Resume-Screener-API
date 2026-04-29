"""
Health & utility routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.database.repository import SubmissionRepository
from app.models.schemas import (
    AnalyzeResponse,
    HealthResponse,
    SubmissionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & History"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Verify that the API, database, and AI provider are properly configured.",
)
async def health_check(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Check API health, database connectivity, and AI provider configuration."""
    # Test DB connection
    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        db_status = "disconnected"

    # Check AI key presence
    ai_key_present = bool(settings.active_api_key)
    if not ai_key_present:
        logger.warning("AI API key is not configured for provider: %s", settings.AI_PROVIDER)

    return HealthResponse(
        status="healthy" if db_status == "connected" and ai_key_present else "degraded",
        database=db_status,
        ai_provider=settings.AI_PROVIDER,
        ai_model=settings.active_model,
    )


@router.get(
    "/submissions",
    response_model=SubmissionListResponse,
    summary="List past submissions",
    description="Retrieve paginated list of past analysis submissions, newest first.",
)
async def list_submissions(
    limit: int = Query(default=20, ge=1, le=100, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_db),
) -> SubmissionListResponse:
    """Retrieve past analysis submissions with pagination."""
    repo = SubmissionRepository(session)

    try:
        submissions = await repo.get_all(limit=limit, offset=offset)
        total = await repo.count()
    except Exception as e:
        logger.exception("Failed to retrieve submissions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submissions.",
        )

    return SubmissionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        submissions=[AnalyzeResponse.model_validate(s) for s in submissions],
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=AnalyzeResponse,
    summary="Get a specific submission",
    description="Retrieve a single analysis result by its ID.",
)
async def get_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Retrieve a specific analysis submission by ID."""
    repo = SubmissionRepository(session)

    submission = await repo.get_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {submission_id} not found.",
        )

    return AnalyzeResponse.model_validate(submission)
