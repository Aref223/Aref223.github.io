"""
User management schemas for user operations.

This module contains Pydantic models for user-related requests and responses
including user creation, updates, and user information retrieval.
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.user import UserRole, UserStatus

class UserBase(BaseModel):
    """Base user model with common fields."""
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING

    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.strip()

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip() if v else None

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            import re
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 7 or len(digits_only) > 15:
                raise ValueError('Phone number must be 7-15 digits')
        return v

class UserCreate(UserBase):
    """Request model for user creation."""
    password: str

    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

class UserUpdate(BaseModel):
    """Request model for user updates."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip() if v else None

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            import re
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 7 or len(digits_only) > 15:
                raise ValueError('Phone number must be 7-15 digits')
        return v

class UserResponse(BaseModel):
    """Response model for user information."""
    id: int
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    role: str
    status: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UserListResponse(BaseModel):
    """Response model for user list."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int

class UserStats(BaseModel):
    """User statistics model."""
    total_users: int
    active_users: int
    verified_users: int
    admin_users: int
    scraper_users: int
    recent_registrations: int
    recent_logins: int

class UserActivity(BaseModel):
    """User activity model."""
    user_id: int
    username: str
    activity_type: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }