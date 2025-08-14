"""
Pydantic schemas for the Visa and Debit Card Scraper application.

This package contains all Pydantic models for request/response validation,
data serialization, and API documentation.
"""

from .auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordChangeRequest
)
from .user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse
)
from .card import (
    CardDataCreate,
    CardDataUpdate,
    CardDataResponse,
    CardDataListResponse,
    CardValidationRequest,
    CardValidationResponse
)
from .scraping import (
    ScrapingJobCreate,
    ScrapingJobUpdate,
    ScrapingJobResponse,
    ScrapingJobListResponse,
    ScrapingRequest,
    ScrapingResponse
)
from .validation import (
    ValidationRequest,
    ValidationResponse,
    ValidationResultResponse,
    ValidationResultListResponse
)

__all__ = [
    # Auth schemas
    "LoginRequest", "LoginResponse", "RegisterRequest", "RegisterResponse",
    "TokenRefreshRequest", "TokenRefreshResponse", "PasswordChangeRequest",
    
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserListResponse",
    
    # Card schemas
    "CardDataCreate", "CardDataUpdate", "CardDataResponse", "CardDataListResponse",
    "CardValidationRequest", "CardValidationResponse",
    
    # Scraping schemas
    "ScrapingJobCreate", "ScrapingJobUpdate", "ScrapingJobResponse", "ScrapingJobListResponse",
    "ScrapingRequest", "ScrapingResponse",
    
    # Validation schemas
    "ValidationRequest", "ValidationResponse", "ValidationResultResponse", "ValidationResultListResponse"
]