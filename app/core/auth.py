"""
Authentication module for JWT token handling and user authentication.

This module provides comprehensive authentication functionality including
JWT token creation, validation, and user authentication services.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.utils.security import log_security_event

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class AuthManager:
    """
    Authentication manager for handling JWT tokens and user authentication.
    
    This class provides methods for creating, validating, and managing
    JWT tokens for user authentication.
    """
    
    def __init__(self):
        """Initialize authentication manager."""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            expires_delta: Optional custom expiration time
            
        Returns:
            str: JWT access token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            data: Data to encode in the token
            
        Returns:
            str: JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            dict: Decoded token data
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            token_type = payload.get("type")
            if not token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return payload
            
        except jwt.PyJWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def create_tokens_for_user(self, user: User) -> Dict[str, str]:
        """
        Create both access and refresh tokens for a user.
        
        Args:
            user: User object
            
        Returns:
            dict: Dictionary containing access and refresh tokens
        """
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            db: Database session
            username: Username
            password: Plain text password
            
        Returns:
            User: Authenticated user or None if authentication fails
        """
        try:
            # Find user by username
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {username}")
                return None
            
            # Check if user is locked
            if user.is_locked:
                logger.warning(f"Login attempt for locked user: {username}")
                return None
            
            # Verify password
            if not user.verify_password(password):
                # Increment failed login attempts
                user.increment_login_attempts()
                db.commit()
                
                logger.warning(f"Failed login attempt for user: {username}")
                return None
            
            # Reset login attempts on successful login
            user.reset_login_attempts()
            user.update_last_login()
            db.commit()
            
            # Log successful login
            log_security_event(
                "user_login",
                {
                    "user_id": user.id,
                    "username": user.username,
                    "ip_address": "unknown"  # Would be passed from request context
                },
                "info"
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None
    
    def get_user_by_token(self, db: Session, token: str) -> Optional[User]:
        """
        Get user from JWT token.
        
        Args:
            db: Database session
            token: JWT token
            
        Returns:
            User: User object or None if not found
        """
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            user = db.query(User).filter(User.id == int(user_id)).first()
            
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting user from token: {e}")
            return None


# Global authentication manager instance
auth_manager = AuthManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        user = auth_manager.get_user_by_token(db, token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current verified user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not verified"
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current admin user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_scraper_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current scraper user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current scraper user
        
    Raises:
        HTTPException: If user is not a scraper
    """
    if current_user.role not in [UserRole.SCRAPER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scraper access required"
        )
    return current_user


# Convenience functions
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    return auth_manager.create_access_token(data, expires_delta)


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    return auth_manager.verify_token(token)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    return auth_manager.authenticate_user(db, username, password)


def create_tokens_for_user(user: User) -> Dict[str, str]:
    """Create both access and refresh tokens for a user."""
    return auth_manager.create_tokens_for_user(user)