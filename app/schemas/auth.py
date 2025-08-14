"""
Authentication schemas for login, registration, and token management.

This module contains Pydantic models for authentication-related requests
and responses including login, registration, and token operations.
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime

class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str
    password: str

    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip()

    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class RegisterRequest(BaseModel):
    """Request model for user registration."""
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.strip()

    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip() if v else None

class RegisterResponse(BaseModel):
    """Response model for successful registration."""
    message: str
    user: Dict[str, Any]

class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str

    @validator('refresh_token')
    def validate_refresh_token(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Invalid refresh token')
        return v.strip()

class TokenRefreshResponse(BaseModel):
    """Response model for successful token refresh."""
    access_token: str
    token_type: str
    expires_in: int

class PasswordChangeRequest(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str

    @validator('current_password', 'new_password')
    def validate_passwords(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @validator('new_password')
    def validate_new_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v