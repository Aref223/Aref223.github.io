"""
User model for authentication and user management.

This module defines the User model with secure password handling,
role-based access control, and audit fields.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
import enum
from datetime import datetime, timedelta

from app.database import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    SCRAPER = "scraper"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base):
    """
    User model for authentication and user management.
    
    This model includes secure password handling, role-based access control,
    and comprehensive audit fields for tracking user activity.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User identification
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # Security fields
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Profile information
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    company = Column(String(200))
    
    # Security and audit fields
    last_login = Column(DateTime(timezone=True))
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True), default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    scraping_jobs = relationship("ScrapingJob", back_populates="user")
    validation_results = relationship("ValidationResult", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_scraper(self) -> bool:
        """Check if user has scraper role."""
        return self.role == UserRole.SCRAPER
    
    def verify_password(self, plain_password: str) -> bool:
        """
        Verify a plain text password against the hashed password.
        
        Args:
            plain_password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, self.hashed_password)
    
    def set_password(self, plain_password: str) -> None:
        """
        Set a new password for the user.
        
        Args:
            plain_password: Plain text password to hash and store
        """
        self.hashed_password = pwd_context.hash(plain_password)
        self.password_changed_at = datetime.utcnow()
    
    def increment_login_attempts(self) -> None:
        """Increment failed login attempts and lock account if necessary."""
        self.login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def reset_login_attempts(self) -> None:
        """Reset failed login attempts and unlock account."""
        self.login_attempts = 0
        self.locked_until = None
    
    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        self.reset_login_attempts()
    
    def to_dict(self) -> dict:
        """
        Convert user object to dictionary representation.
        
        Returns:
            dict: User data as dictionary
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "status": self.status.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "company": self.company,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        **kwargs
    ) -> "User":
        """
        Create a new user with proper password hashing.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password
            role: User role
            **kwargs: Additional user attributes
            
        Returns:
            User: Newly created user instance
        """
        user = cls(
            username=username,
            email=email,
            role=role,
            **kwargs
        )
        user.set_password(password)
        return user