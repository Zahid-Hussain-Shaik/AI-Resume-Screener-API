"""
Database repository — CRUD operations for submissions.
Keeps all raw SQL/ORM queries isolated from business logic.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Submission, User


class UserRepository:
    """Data access layer for the users table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


class SubmissionRepository:
    """Data access layer for the submissions table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, submission: Submission) -> Submission:
        """Insert a new submission and return it with the generated ID."""
        self.session.add(submission)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def get_by_id(self, submission_id: int) -> Submission | None:
        """Retrieve a single submission by its primary key."""
        result = await self.session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int, limit: int = 20, offset: int = 0) -> list[Submission]:
        """Retrieve submissions for a specific user."""
        result = await self.session.execute(
            select(Submission)
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """Return total number of submissions for a user."""
        result = await self.session.execute(
            select(func.count(Submission.id)).where(Submission.user_id == user_id)
        )
        return result.scalar_one()

    async def delete(self, submission_id: int, user_id: int) -> bool:
        """Delete a submission if it belongs to the user."""
        result = await self.session.execute(
            delete(Submission)
            .where(Submission.id == submission_id)
            .where(Submission.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount > 0
