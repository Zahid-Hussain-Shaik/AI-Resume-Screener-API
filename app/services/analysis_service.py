"""
Analysis service — orchestrates the full resume analysis workflow.
Bridges the AI service with database persistence.
"""

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.repository import SubmissionRepository
from app.models.database import Submission
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates: validate input → call AI → persist results → return response."""

    def __init__(self, ai_service: AIService, settings: Settings):
        self.ai_service = ai_service
        self.settings = settings

    async def analyze_resume(
        self,
        resume_text: str,
        job_description: str | None = None,
        scan_type: str = "match",
        user_id: int | None = None,
        session: AsyncSession = None,
    ) -> AnalyzeResponse:
        """
        Run a full resume analysis pipeline.
        """
        repo = SubmissionRepository(session)

        # ── Step 1: Call AI with timing ──
        start_time = time.perf_counter()

        try:
            ai_result = await self.ai_service.analyze(
                resume_text=resume_text,
                job_description=job_description,
                scan_type=scan_type,
            )
        except Exception as e:
            logger.error("AI analysis failed: %s", str(e))
            raise

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info("%s analysis completed in %dms", scan_type, elapsed_ms)

        # ── Step 2: Persist to database ──
        submission = Submission(
            user_id=user_id,
            scan_type=scan_type,
            resume_text=resume_text,
            job_description=job_description,
            ai_provider=self.settings.AI_PROVIDER,
            ai_model=self.settings.active_model,
            processing_time_ms=elapsed_ms,
        )

        if scan_type == "match":
            submission.overall_score = ai_result.get("match_score", 0.0)
            submission.missing_skills = ai_result.get("missing_skills", [])
            submission.rewrite_suggestions = ai_result.get("rewrite_suggestions", [])
        else:
            submission.overall_score = ai_result.get("overall_score", 0.0)
            submission.formatting_score = ai_result.get("formatting_score", 0.0)
            submission.readability_score = ai_result.get("readability_score", 0.0)
            submission.keyword_score = ai_result.get("keyword_score", 0.0)
            submission.detailed_results = ai_result  # store full JSON for detail

        submission = await repo.create(submission)
        logger.info("Submission persisted with ID=%d", submission.id)

        # ── Step 3: Build response ──
        # Manual mapping might be safer due to JSON aliasing
        data = {
            "id": submission.id,
            "scan_type": submission.scan_type,
            "overall_score": submission.overall_score,
            "match_score": submission.overall_score if scan_type == "match" else None,
            "missing_skills": submission.missing_skills,
            "rewrite_suggestions": submission.rewrite_suggestions,
            "formatting_score": submission.formatting_score,
            "readability_score": submission.readability_score,
            "keyword_score": submission.keyword_score,
            "missing_sections": ai_result.get("missing_sections", []),
            "weak_bullet_points": ai_result.get("weak_bullet_points", []),
            "keyword_analysis": ai_result.get("keyword_analysis", []),
            "improvement_suggestions": ai_result.get("improvement_suggestions", []),
            "ai_provider": submission.ai_provider,
            "ai_model": submission.ai_model,
            "processing_time_ms": submission.processing_time_ms,
            "created_at": submission.created_at,
        }
        return AnalyzeResponse(**data)
