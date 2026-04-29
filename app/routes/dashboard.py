from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database.repository import SubmissionRepository
from app.models.database import User
from app.models.schemas import AnalyzeResponse, SubmissionListResponse
from app.routes.dependencies import get_current_user

router = APIRouter(prefix="/history", tags=["Dashboard"])


@router.get("", response_model=SubmissionListResponse)
async def get_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve history for the current user."""
    repo = SubmissionRepository(session)
    submissions = await repo.get_all_by_user(current_user.id, limit=limit, offset=offset)
    total = await repo.count_by_user(current_user.id)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "submissions": [AnalyzeResponse.model_validate(s) for s in submissions],
    }


@router.get("/{submission_id}", response_model=AnalyzeResponse)
async def get_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve a specific submission."""
    repo = SubmissionRepository(session)
    submission = await repo.get_by_id(submission_id)
    
    if not submission or submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )
    
    return AnalyzeResponse.model_validate(submission)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a submission."""
    repo = SubmissionRepository(session)
    success = await repo.delete(submission_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found or unauthorized",
        )
    
    return None
