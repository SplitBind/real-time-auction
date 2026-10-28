"""
Application Configuration Module
--------------------------------
Loads, validates, and centralizes environment variables and application 
settings using Pydantic BaseSettings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
class Settings(BaseSettings):
    APP_NAME: str = "Real-Time Auction API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # uploads directory
    UPLOAD_DIR: Path = BASE_DIR / "static" / "uploads"

    model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
            )

settings = Settings()
