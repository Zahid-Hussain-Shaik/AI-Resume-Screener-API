import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import Settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and security logic."""

    def __init__(self, settings: Settings):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def hash_password(self, password: str) -> str:
        """Hash a plain text password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict[str, Any]) -> str:
        """Generate a new JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError as e:
            logger.warning("Token decoding failed: %s", e)
            return None
