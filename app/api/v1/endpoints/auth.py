"""
Authentication endpoints for login, registration, and token management.

This module provides API endpoints for user authentication including
login, registration, token refresh, and password management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app.core.auth import (
    authenticate_user,
    create_tokens_for_user,
    get_current_user,
    auth_manager
)
from app.models.user import User, UserRole, UserStatus
from app.utils.security import validate_input, log_security_event
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordChangeRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        username_validation = validate_input(login_data.username, "general")
        if not username_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username format")
        
        user = authenticate_user(db, login_data.username, login_data.password)
        if not user:
            log_security_event("login_failed", {
                "username": login_data.username,
                "ip_address": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }, "warning")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        
        if not user.is_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not verified. Please verify your email first.")
        
        tokens = create_tokens_for_user(user)
        log_security_event("login_successful", {
            "user_id": user.id,
            "username": user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
            "user": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")

@router.post("/register", response_model=RegisterResponse)
async def register(register_data: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        username_validation = validate_input(register_data.username, "general")
        email_validation = validate_input(register_data.email, "email")
        password_validation = validate_input(register_data.password, "general")
        
        if not username_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username format")
        if not email_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
        if not password_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password format")
        
        if db.query(User).filter(User.username == register_data.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        if db.query(User).filter(User.email == register_data.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
        user = User.create_user(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            role=UserRole.USER,
            status=UserStatus.PENDING
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log_security_event("user_registered", {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {
            "message": "User registered successfully. Please verify your email.",
            "user": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(refresh_data: TokenRefreshRequest, request: Request) -> Dict[str, Any]:
    try:
        payload = auth_manager.verify_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        
        token_data = {
            "sub": payload["sub"],
            "username": payload["username"],
            "email": payload["email"],
            "role": payload["role"],
            "is_active": payload["is_active"],
            "is_verified": payload["is_verified"]
        }
        
        new_access_token = auth_manager.create_access_token(token_data)
        
        log_security_event("token_refreshed", {
            "user_id": payload["sub"],
            "username": payload["username"],
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": auth_manager.access_token_expire_minutes * 60
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed")

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    log_security_event("user_logout", {
        "user_id": current_user.id,
        "username": current_user.username,
        "ip_address": request.client.host if request.client else "unknown"
    }, "info")
    return {"message": "Successfully logged out"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    try:
        if not current_user.verify_password(password_data.current_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        
        password_validation = validate_input(password_data.new_password, "general")
        if not password_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid new password format")
        
        current_user.set_password(password_data.new_password)
        db.commit()
        
        log_security_event("password_changed", {
            "user_id": current_user.id,
            "username": current_user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password change failed")

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"user": current_user.to_dict()}

@router.post("/verify-email")
async def verify_email(token: str, request: Request, db: Session = Depends(get_db)) -> Dict[str, str]:
    try:
        payload = auth_manager.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
        
        user.is_verified = True
        user.status = UserStatus.ACTIVE
        db.commit()
        
        log_security_event("email_verified", {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": "Email verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email verification failed")