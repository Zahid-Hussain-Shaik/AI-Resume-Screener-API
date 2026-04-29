"""
SQLAlchemy ORM models for the resume screener database.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    """Users of the platform."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="user", cascade="all, delete-orphan")


class Submission(Base):
    """Stores each resume analysis submission (ATS Check or JD Match)."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Type of scan: 'ats' or 'match'
    scan_type: Mapped[str] = mapped_column(String(20), nullable=False, default="match")

    # Input data
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Results (Common)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rewrite_suggestions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ATS Specific results (stored in JSON for flexibility or as separate columns)
    # We'll use separate columns for key scores to allow better querying later
    formatting_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    detailed_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metadata
    ai_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="submissions")

    def __repr__(self) -> str:
        return (
            f"<Submission(id={self.id}, type={self.scan_type}, score={self.overall_score}, "
            f"user={self.user_id})>"
        )
