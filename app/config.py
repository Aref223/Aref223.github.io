"""
Configuration module for the Visa and Debit Card Scraper application.

This module handles all configuration settings including database connections,
security settings, API configurations, and environment-specific variables.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Settings
    APP_NAME: str = "Visa and Debit Card Scraper"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Settings
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Visa Scraper API"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Scraping Settings
    SCRAPER_TIMEOUT: int = 30
    SCRAPER_RETRY_ATTEMPTS: int = 3
    SCRAPER_DELAY_BETWEEN_REQUESTS: float = 1.0
    MAX_CONCURRENT_SCRAPERS: int = 5
    
    # Validation Settings
    CARD_VALIDATION_ENABLED: bool = True
    EMAIL_VALIDATION_ENABLED: bool = True
    PHONE_VALIDATION_ENABLED: bool = True
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["csv", "xlsx", "json"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Encryption
    ENCRYPTION_KEY: str
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Assemble CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v):
        """Validate secret key length."""
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("ENCRYPTION_KEY", pre=True)
    def validate_encryption_key(cls, v):
        """Validate encryption key length."""
        if not v or len(v) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters long")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Environment-specific configurations
if settings.ENVIRONMENT == "development":
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"
elif settings.ENVIRONMENT == "testing":
    settings.DEBUG = True
    settings.DATABASE_URL = "sqlite:///./test.db"
    settings.REDIS_URL = "redis://localhost:6379/1"