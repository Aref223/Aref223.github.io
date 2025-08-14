"""
User management endpoints for user operations.

This module provides API endpoints for user management including
user creation, updates, deletion, and user information retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
import logging

from app.database import get_db
from app.core.auth import get_current_user, get_current_admin_user
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserStats
)
from app.utils.security import validate_input, log_security_event

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    status: Optional[UserStatus] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of users with optional filtering."""
    try:
        query = db.query(User)
        
        # Apply filters
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if role:
            query = query.filter(User.role == role)
        
        if status:
            query = query.filter(User.status == status)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        users = query.offset((page - 1) * size).limit(size).all()
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        return {
            "users": [UserResponse.from_orm(user) for user in users],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve users")

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Create a new user (admin only)."""
    try:
        # Validate input
        username_validation = validate_input(user_data.username, "general")
        email_validation = validate_input(user_data.email, "email")
        
        if not username_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username format")
        if not email_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
        
        # Check if username or email already exists
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        
        # Create user
        user = User.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            company=user_data.company,
            phone=user_data.phone,
            role=user_data.role,
            status=user_data.status
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log_security_event("user_created", {
            "created_by": current_user.id,
            "new_user_id": user.id,
            "new_username": user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get user by ID (users can only see their own profile, admins can see all)."""
    try:
        # Users can only see their own profile unless they're admin
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update user information (users can only update their own profile, admins can update all)."""
    try:
        # Users can only update their own profile unless they're admin
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        log_security_event("user_updated", {
            "updated_by": current_user.id,
            "user_id": user.id,
            "username": user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete user (admin only)."""
    try:
        if current_user.id == user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        username = user.username
        db.delete(user)
        db.commit()
        
        log_security_event("user_deleted", {
            "deleted_by": current_user.id,
            "deleted_user_id": user_id,
            "deleted_username": username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": f"User {username} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete user")

@router.get("/stats/overview", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> UserStats:
    """Get user statistics (admin only)."""
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        verified_users = db.query(User).filter(User.is_verified == True).count()
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
        scraper_users = db.query(User).filter(User.role == UserRole.SCRAPER).count()
        
        # Recent registrations (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = db.query(User).filter(User.created_at >= thirty_days_ago).count()
        
        # Recent logins (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = db.query(User).filter(User.last_login >= seven_days_ago).count()
        
        return UserStats(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            admin_users=admin_users,
            scraper_users=scraper_users,
            recent_registrations=recent_registrations,
            recent_logins=recent_logins
        )
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user statistics")

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Activate a user account (admin only)."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        user.is_active = True
        user.status = UserStatus.ACTIVE
        db.commit()
        
        log_security_event("user_activated", {
            "activated_by": current_user.id,
            "user_id": user.id,
            "username": user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": f"User {user.username} activated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate user")

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Deactivate a user account (admin only)."""
    try:
        if current_user.id == user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        user.is_active = False
        user.status = UserStatus.INACTIVE
        db.commit()
        
        log_security_event("user_deactivated", {
            "deactivated_by": current_user.id,
            "user_id": user.id,
            "username": user.username,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": f"User {user.username} deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to deactivate user")