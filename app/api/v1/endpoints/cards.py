"""
Card data endpoints for card management operations.

This module provides API endpoints for card data management including
card creation, updates, retrieval, and card information management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
import logging

from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, UserRole
from app.models.card_data import CardData, CardType, CardStatus
from app.schemas.card import (
    CardDataCreate,
    CardDataUpdate,
    CardDataResponse,
    CardDataListResponse,
    CardValidationRequest,
    CardValidationResponse,
    CardStats,
    CardSearchRequest
)
from app.utils.validation import comprehensive_card_validation
from app.utils.security import validate_input, log_security_event

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=CardDataListResponse)
async def get_cards(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    card_type: Optional[CardType] = Query(None),
    card_status: Optional[CardStatus] = Query(None),
    is_valid: Optional[bool] = Query(None),
    bank_name: Optional[str] = Query(None),
    country_issued: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of cards with optional filtering."""
    try:
        query = db.query(CardData)
        
        # Users can only see their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        # Apply filters
        if card_type:
            query = query.filter(CardData.card_type == card_type)
        if card_status:
            query = query.filter(CardData.card_status == card_status)
        if is_valid is not None:
            query = query.filter(CardData.is_valid == is_valid)
        if bank_name:
            query = query.filter(CardData.bank_name.ilike(f"%{bank_name}%"))
        if country_issued:
            query = query.filter(CardData.country_issued.ilike(f"%{country_issued}%"))
        if search:
            search_filter = or_(
                CardData.bank_name.ilike(f"%{search}%"),
                CardData.country_issued.ilike(f"%{search}%"),
                CardData.card_level.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        cards = query.order_by(desc(CardData.created_at)).offset((page - 1) * size).limit(size).all()
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        # Calculate stats
        stats = {
            "total_cards": total,
            "valid_cards": db.query(CardData).filter(CardData.is_valid == True).count(),
            "invalid_cards": db.query(CardData).filter(CardData.is_valid == False).count(),
            "visa_cards": db.query(CardData).filter(CardData.card_type == CardType.VISA).count(),
            "mastercard_cards": db.query(CardData).filter(CardData.card_type == CardType.MASTERCARD).count(),
            "amex_cards": db.query(CardData).filter(CardData.card_type == CardType.AMEX).count(),
            "discover_cards": db.query(CardData).filter(CardData.card_type == CardType.DISCOVER).count(),
            "unknown_cards": db.query(CardData).filter(CardData.card_type == CardType.UNKNOWN).count()
        }
        
        return {
            "cards": [CardDataResponse.from_orm(card) for card in cards],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting cards: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve cards")

@router.post("/", response_model=CardDataResponse)
async def create_card(
    card_data: CardDataCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CardDataResponse:
    """Create a new card record."""
    try:
        # Validate card number
        card_validation = validate_input(card_data.card_number, "card_number")
        if not card_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid card number")
        
        # Check if card already exists (by hash)
        from app.utils.validation import hash_card_number
        card_hash = hash_card_number(card_data.card_number)
        existing_card = db.query(CardData).filter(CardData.card_number_hash == card_hash).first()
        if existing_card:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card already exists")
        
        # Create card data record
        card = CardData.create_card_data(
            user_id=current_user.id,
            card_number=card_data.card_number,
            card_type=card_data.card_type,
            expiry_date=card_data.expiry_date,
            cvv=card_data.cvv,
            cardholder_name=card_data.cardholder_name,
            bank_name=card_data.bank_name,
            card_level=card_data.card_level,
            country_issued=card_data.country_issued,
            currency=card_data.currency,
            source_url=card_data.source_url
        )
        
        # Perform validation
        validation_result = comprehensive_card_validation(
            card_data.card_number,
            card_data.expiry_date or "",
            card_data.cvv or "",
            card_data.cardholder_name
        )
        
        # Update validation status
        card.update_validation_status(
            validation_result["overall_valid"],
            validation_result["score"],
            validation_result["errors"],
            validation_result["warnings"]
        )
        
        db.add(card)
        db.commit()
        db.refresh(card)
        
        log_security_event("card_created", {
            "user_id": current_user.id,
            "card_id": card.id,
            "card_type": card.card_type.value,
            "is_valid": card.is_valid,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return CardDataResponse.from_orm(card)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating card: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create card")

@router.get("/{card_id}", response_model=CardDataResponse)
async def get_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CardDataResponse:
    """Get card by ID."""
    try:
        query = db.query(CardData).filter(CardData.id == card_id)
        
        # Users can only see their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        card = query.first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        
        return CardDataResponse.from_orm(card)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting card {card_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve card")

@router.put("/{card_id}", response_model=CardDataResponse)
async def update_card(
    card_id: int,
    card_data: CardDataUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CardDataResponse:
    """Update card information."""
    try:
        query = db.query(CardData).filter(CardData.id == card_id)
        
        # Users can only update their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        card = query.first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        
        # Update fields
        update_data = card_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)
        
        db.commit()
        db.refresh(card)
        
        log_security_event("card_updated", {
            "user_id": current_user.id,
            "card_id": card.id,
            "updated_fields": list(update_data.keys()),
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return CardDataResponse.from_orm(card)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating card {card_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update card")

@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete card."""
    try:
        query = db.query(CardData).filter(CardData.id == card_id)
        
        # Users can only delete their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        card = query.first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        
        db.delete(card)
        db.commit()
        
        log_security_event("card_deleted", {
            "user_id": current_user.id,
            "card_id": card_id,
            "card_type": card.card_type.value,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": "Card deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting card {card_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete card")

@router.post("/{card_id}/validate", response_model=CardValidationResponse)
async def validate_card(
    card_id: int,
    validation_request: CardValidationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CardValidationResponse:
    """Validate a specific card."""
    try:
        query = db.query(CardData).filter(CardData.id == card_id)
        
        # Users can only validate their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        card = query.first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        
        # Get card number for validation
        card_number = card.get_card_number()
        if not card_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot retrieve card number")
        
        # Perform validation
        validation_result = comprehensive_card_validation(
            card_number,
            validation_request.expiry_date or "",
            validation_request.cvv or "",
            validation_request.cardholder_name
        )
        
        # Update card validation status
        card.update_validation_status(
            validation_result["overall_valid"],
            validation_result["score"],
            validation_result["errors"],
            validation_result["warnings"]
        )
        
        db.commit()
        
        log_security_event("card_validated", {
            "user_id": current_user.id,
            "card_id": card.id,
            "is_valid": validation_result["overall_valid"],
            "validation_score": validation_result["score"],
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return CardValidationResponse(
            card_number=card_number,
            card_type=card.card_type.value,
            is_valid=validation_result["overall_valid"],
            validation_score=validation_result["score"],
            validation_details=validation_result,
            validation_errors=validation_result.get("errors", []),
            validation_warnings=validation_result.get("warnings", []),
            bank_info={
                "bank_name": card.bank_name,
                "card_level": card.card_level,
                "country": card.country_issued
            } if card.bank_name else None,
            country_info={
                "country": card.country_issued,
                "currency": card.currency
            } if card.country_issued else None,
            validation_time_ms=0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating card {card_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Card validation failed")

@router.get("/stats/overview", response_model=CardStats)
async def get_card_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CardStats:
    """Get card statistics."""
    try:
        query = db.query(CardData)
        
        # Users can only see their own stats unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        total_cards = query.count()
        valid_cards = query.filter(CardData.is_valid == True).count()
        invalid_cards = query.filter(CardData.is_valid == False).count()
        
        # Card type counts
        visa_cards = query.filter(CardData.card_type == CardType.VISA).count()
        mastercard_cards = query.filter(CardData.card_type == CardType.MASTERCARD).count()
        amex_cards = query.filter(CardData.card_type == CardType.AMEX).count()
        discover_cards = query.filter(CardData.card_type == CardType.DISCOVER).count()
        unknown_cards = query.filter(CardData.card_type == CardType.UNKNOWN).count()
        
        # Calculate average validation score
        avg_score_result = db.query(CardData.validation_score).filter(CardData.validation_score > 0).scalar()
        average_validation_score = float(avg_score_result) if avg_score_result else 0.0
        
        # Recent scrapes (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_scrapes = query.filter(CardData.scraped_at >= seven_days_ago).count()
        
        return CardStats(
            total_cards=total_cards,
            valid_cards=valid_cards,
            invalid_cards=invalid_cards,
            visa_cards=visa_cards,
            mastercard_cards=mastercard_cards,
            amex_cards=amex_cards,
            discover_cards=discover_cards,
            unknown_cards=unknown_cards,
            average_validation_score=average_validation_score,
            recent_scrapes=recent_scrapes
        )
    except Exception as e:
        logger.error(f"Error getting card stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve card statistics")

@router.post("/search", response_model=CardDataListResponse)
async def search_cards(
    search_request: CardSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Search cards with advanced filters."""
    try:
        query = db.query(CardData)
        
        # Users can only search their own cards unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(CardData.user_id == current_user.id)
        
        # Apply filters
        if search_request.card_type:
            query = query.filter(CardData.card_type == search_request.card_type)
        if search_request.card_status:
            query = query.filter(CardData.card_status == search_request.card_status)
        if search_request.bank_name:
            query = query.filter(CardData.bank_name.ilike(f"%{search_request.bank_name}%"))
        if search_request.country_issued:
            query = query.filter(CardData.country_issued.ilike(f"%{search_request.country_issued}%"))
        if search_request.is_valid is not None:
            query = query.filter(CardData.is_valid == search_request.is_valid)
        if search_request.min_validation_score is not None:
            query = query.filter(CardData.validation_score >= search_request.min_validation_score)
        if search_request.max_validation_score is not None:
            query = query.filter(CardData.validation_score <= search_request.max_validation_score)
        if search_request.date_from:
            query = query.filter(CardData.created_at >= search_request.date_from)
        if search_request.date_to:
            query = query.filter(CardData.created_at <= search_request.date_to)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        cards = query.order_by(desc(CardData.created_at)).offset((search_request.page - 1) * search_request.size).limit(search_request.size).all()
        
        # Calculate pagination info
        pages = (total + search_request.size - 1) // search_request.size
        
        # Calculate stats
        stats = {
            "total_cards": total,
            "valid_cards": query.filter(CardData.is_valid == True).count(),
            "invalid_cards": query.filter(CardData.is_valid == False).count(),
            "average_score": db.query(CardData.validation_score).filter(CardData.validation_score > 0).scalar() or 0
        }
        
        return {
            "cards": [CardDataResponse.from_orm(card) for card in cards],
            "total": total,
            "page": search_request.page,
            "size": search_request.size,
            "pages": pages,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error searching cards: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search cards")