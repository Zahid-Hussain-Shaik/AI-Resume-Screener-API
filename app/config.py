"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — all values loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Database ----
    DATABASE_URL: str = "mysql+aiomysql://root:rootpassword123@db:3306/resume_screener"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ---- AI Provider ----
    AI_PROVIDER: Literal["openai", "anthropic"] = "openai"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # AI Settings
    AI_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 3

    # ---- App ----
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]

    # ---- Auth ----
    SECRET_KEY: str = "your-super-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # ---- Derived ----
    @property
    def active_api_key(self) -> str:
        """Return the API key for the currently configured provider."""
        if self.AI_PROVIDER == "openai":
            return self.OPENAI_API_KEY
        return self.ANTHROPIC_API_KEY

    @property
    def active_model(self) -> str:
        """Return the model name for the currently configured provider."""
        if self.AI_PROVIDER == "openai":
            return self.OPENAI_MODEL
        return self.ANTHROPIC_MODEL


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — settings are loaded once and reused."""
    return Settings()
