from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.connection import get_db
from app.database.repository import UserRepository
from app.models.database import User
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
) -> User:
    """Validate token and return current user."""
    auth_service = AuthService(settings)
    payload = auth_service.decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user information",
        )
    
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
) -> User | None:
    """Return user if token is present, otherwise None."""
    if not token:
        return None
    try:
        return await get_current_user(token, session, settings)
    except HTTPException:
        return None
