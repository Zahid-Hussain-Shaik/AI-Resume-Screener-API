"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
#  Request Schemas
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Input payload for the /analyze endpoint."""

    resume_text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="The full text content of the resume.",
        examples=["Experienced software engineer with 5+ years in Python, FastAPI, and cloud services..."],
    )
    job_description: str = Field(
        ...,
        min_length=50,
        max_length=20000,
        description="The full text of the job description to match against.",
        examples=["We are looking for a Senior Backend Engineer with expertise in Python, REST APIs..."],
    )

    @field_validator("resume_text", "job_description")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        """Reject strings that are technically long enough but contain only whitespace."""
        if not v.strip():
            raise ValueError("Field must contain meaningful text, not just whitespace.")
        return v.strip()


# ──────────────────────────────────────────────
#  Auth Schemas
# ──────────────────────────────────────────────

class UserSignup(BaseModel):
    email: str
    password: str
    full_name: str | None = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Response Schemas
# ──────────────────────────────────────────────

class RewriteSuggestion(BaseModel):
    """A single rewrite suggestion for improving the resume."""

    section: str = Field(..., description="The resume section (e.g., 'Summary').")
    original: str = Field(..., description="The original text.")
    suggested: str = Field(..., description="The improved version.")
    rationale: str = Field(..., description="Why this helps.")


class WeakBulletPoint(BaseModel):
    original: str
    issue: str
    suggested: str


class AnalyzeResponse(BaseModel):
    """Full analysis result."""

    id: int
    scan_type: str
    overall_score: float
    
    # JD Match fields
    match_score: float | None = None
    missing_skills: list[str] = []
    rewrite_suggestions: list[RewriteSuggestion] = []
    
    # ATS Check fields
    formatting_score: float | None = None
    readability_score: float | None = None
    keyword_score: float | None = None
    missing_sections: list[str] = []
    weak_bullet_points: list[WeakBulletPoint] = []
    keyword_analysis: list[str] = []
    improvement_suggestions: list[str] = []
    
    ai_provider: str
    ai_model: str
    processing_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    ai_provider: str
    ai_model: str


class ErrorResponse(BaseModel):
    """Standardized error response."""

    detail: str
    error_code: str = "INTERNAL_ERROR"


class SubmissionListResponse(BaseModel):
    """Paginated list of submissions."""

    total: int
    limit: int
    offset: int
    submissions: list[AnalyzeResponse]
