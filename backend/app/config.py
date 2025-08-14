from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite:///./app.db")
    JWT_SECRET: str = Field(default="change_me_please")
    FERNET_KEY: str = Field(default="")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    SCRAPER_USER_AGENT: str = Field(default="VisaDebitScraperBot/1.0")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

settings = Settings()  # Loaded at import time