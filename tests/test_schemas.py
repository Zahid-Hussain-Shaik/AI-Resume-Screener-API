"""
Tests for Pydantic schemas — input validation edge cases.
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, RewriteSuggestion


class TestAnalyzeRequest:
    """Validate input constraints on AnalyzeRequest."""

    def _valid_payload(self, **overrides) -> dict:
        """Generate a valid payload, overriding specific fields."""
        base = {
            "resume_text": "A" * 100,  # Min length = 50
            "job_description": "B" * 100,
        }
        base.update(overrides)
        return base

    def test_valid_input(self):
        req = AnalyzeRequest(**self._valid_payload())
        assert len(req.resume_text) >= 50
        assert len(req.job_description) >= 50

    def test_resume_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(**self._valid_payload(resume_text="Short"))
        assert "resume_text" in str(exc_info.value)

    def test_job_description_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(**self._valid_payload(job_description="Short"))
        assert "job_description" in str(exc_info.value)

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(**self._valid_payload(resume_text=" " * 100))

    def test_resume_too_long(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(**self._valid_payload(resume_text="A" * 50001))

    def test_missing_resume(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(job_description="B" * 100)

    def test_missing_job_description(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(resume_text="A" * 100)

    def test_strips_whitespace(self):
        req = AnalyzeRequest(**self._valid_payload(resume_text="  " + "A" * 100 + "  "))
        assert not req.resume_text.startswith(" ")
        assert not req.resume_text.endswith(" ")


class TestRewriteSuggestion:
    """Test rewrite suggestion schema."""

    def test_valid_suggestion(self):
        suggestion = RewriteSuggestion(
            section="Summary",
            original="I did things",
            suggested="Engineered scalable microservices",
            rationale="More specific and impactful",
        )
        assert suggestion.section == "Summary"

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            RewriteSuggestion(
                section="Summary",
                original="text",
                # missing suggested and rationale
            )


class TestAnalyzeResponse:
    """Test response schema validation."""

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            AnalyzeResponse(
                id=1,
                match_score=150,  # Over 100
                missing_skills=[],
                rewrite_suggestions=[],
                ai_provider="openai",
                ai_model="gpt-4o",
                processing_time_ms=500,
                created_at="2025-01-01T00:00:00Z",
            )

    def test_negative_score(self):
        with pytest.raises(ValidationError):
            AnalyzeResponse(
                id=1,
                match_score=-10,
                missing_skills=[],
                rewrite_suggestions=[],
                ai_provider="openai",
                ai_model="gpt-4o",
                processing_time_ms=500,
                created_at="2025-01-01T00:00:00Z",
            )
