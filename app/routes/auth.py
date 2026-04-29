from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.connection import get_db
from app.database.repository import UserRepository
from app.models.database import User
from app.models.schemas import Token, UserOut, UserSignup
from app.services.auth_service import AuthService
from app.routes.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserSignup,
    session: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
):
    """Register a new user."""
    repo = UserRepository(session)
    auth_service = AuthService(settings)
    
    # Check if user exists
    existing = await repo.get_by_email(user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    new_user = User(
        email=user_in.email,
        hashed_password=auth_service.hash_password(user_in.password),
        full_name=user_in.full_name,
    )
    return await repo.create(new_user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
):
    """Authenticate user and return JWT."""
    repo = UserRepository(session)
    auth_service = AuthService(settings)
    
    user = await repo.get_by_email(form_data.username)
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user
