"""
Analyze route — POST /api/v1/analyze
Accepts a resume and job description, returns AI-powered match analysis.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.models.database import User
from app.models.schemas import AnalyzeResponse, ErrorResponse
from app.services.ai_service import get_ai_service
from app.services.analysis_service import AnalysisService
from app.services.file_service import FileService
from app.routes.dependencies import get_optional_user

router = APIRouter(tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Match resume against job description",
)
async def analyze_match(
    resume_file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    job_description: str = Form(...),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_user),
) -> AnalyzeResponse:
    """Analyze how well a resume matches a job description."""
    content = ""
    if resume_file:
        file_bytes = await resume_file.read()
        content = FileService.extract_text(file_bytes, resume_file.filename)
    elif resume_text:
        content = resume_text
    else:
        raise HTTPException(status_code=400, detail="Provide either resume_file or resume_text")

    ai_service = get_ai_service(settings)
    analysis_service = AnalysisService(ai_service, settings)
    
    return await analysis_service.analyze_resume(
        resume_text=content,
        job_description=job_description,
        scan_type="match",
        user_id=current_user.id if current_user else None,
        session=session,
    )


@router.post(
    "/ats-check",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="General ATS resume check",
)
async def analyze_ats(
    resume_file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_user),
) -> AnalyzeResponse:
    """Analyze a resume for general ATS optimization."""
    content = ""
    if resume_file:
        file_bytes = await resume_file.read()
        content = FileService.extract_text(file_bytes, resume_file.filename)
    elif resume_text:
        content = resume_text
    else:
        raise HTTPException(status_code=400, detail="Provide either resume_file or resume_text")

    ai_service = get_ai_service(settings)
    analysis_service = AnalysisService(ai_service, settings)
    
    return await analysis_service.analyze_resume(
        resume_text=content,
        scan_type="ats",
        user_id=current_user.id if current_user else None,
        session=session,
    )
