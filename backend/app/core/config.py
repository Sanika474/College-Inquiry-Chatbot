"""Application configuration module using Pydantic Settings."""

import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CampusIQ Global Configuration Settings."""

    PROJECT_NAME: str = "CampusIQ — Intelligent College Companion"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Sessions
    SECRET_KEY: str = "campusiq_development_insecure_secret_key_change_in_production"
    SESSION_COOKIE_NAME: str = "campusiq_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/campusiq_db"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Optional AI Fallback Configuration
    AI_PROVIDER: Optional[str] = None  # None, "gemini", or "openai"
    AI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-1.5-flash"
    AI_TIMEOUT_SECONDS: float = 10.0

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
