"""
Validation endpoints for card validation operations.

This module provides API endpoints for card validation including
single card validation, batch validation, and validation history.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
import logging
import time

from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, UserRole
from app.models.card_data import CardData, CardType, CardStatus
from app.models.validation_result import ValidationResult, ValidationStatus, ValidationType
from app.schemas.validation import (
    ValidationRequest,
    ValidationResponse,
    ValidationResultResponse,
    ValidationResultListResponse,
    ValidationStats,
    ValidationSearchRequest,
    BatchValidationRequest,
    BatchValidationResponse,
    ValidationHistoryRequest
)
from app.utils.validation import comprehensive_card_validation
from app.utils.security import validate_input, log_security_event, rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/validate", response_model=ValidationResponse)
@rate_limit("validation")
async def validate_card(
    validation_data: ValidationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ValidationResponse:
    """Validate a single card."""
    try:
        start_time = time.time()
        
        # Validate card number
        card_validation = validate_input(validation_data.card_number, "card_number")
        if not card_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid card number")
        
        # Perform comprehensive validation
        validation_result = comprehensive_card_validation(
            validation_data.card_number,
            validation_data.expiry_date or "",
            validation_data.cvv or "",
            validation_data.cardholder_name
        )
        
        # Get additional information if requested
        bank_info = None
        country_info = None
        
        if validation_data.include_bank_info and validation_result["card_type"] != "unknown":
            # In a real implementation, you would call external APIs here
            bank_info = {
                "bank_name": "Sample Bank",
                "card_level": "Standard",
                "country": "US"
            }
        
        if validation_data.include_country_info:
            country_info = {
                "country": "United States",
                "currency": "USD",
                "region": "North America"
            }
        
        validation_time = int((time.time() - start_time) * 1000)
        
        # Store validation result
        validation_record = ValidationResult.create_validation_result(
            user_id=current_user.id,
            card_data_id=None,  # No card data record for single validation
            validation_type=validation_data.validation_type,
            validation_source="api"
        )
        
        # Set validation details
        validation_record.luhn_check_passed = validation_result.get("card_number_valid", False)
        validation_record.expiry_check_passed = validation_result.get("expiry_valid", False)
        validation_record.cvv_check_passed = validation_result.get("cvv_valid", False)
        validation_record.bin_check_passed = validation_result.get("bin_check_passed", False)
        validation_record.bank_check_passed = validation_result.get("bank_check_passed", False)
        validation_record.country_check_passed = validation_result.get("country_check_passed", False)
        
        validation_record.validation_details = {
            "luhn_check": {"passed": validation_result.get("card_number_valid", False)},
            "expiry_check": {"passed": validation_result.get("expiry_valid", False)},
            "cvv_check": {"passed": validation_result.get("cvv_valid", False)},
            "bin_check": {"passed": validation_result.get("bin_check_passed", False)},
            "bank_check": {"passed": validation_result.get("bank_check_passed", False)},
            "country_check": {"passed": validation_result.get("country_check_passed", False)}
        }
        
        validation_record.validation_errors = validation_result.get("errors", [])
        validation_record.validation_warnings = validation_result.get("warnings", [])
        validation_record.card_number_length = len(validation_data.card_number.replace(" ", ""))
        validation_record.card_type_detected = validation_result.get("card_type", "unknown")
        validation_record.bank_name_detected = bank_info.get("bank_name") if bank_info else None
        validation_record.country_detected = country_info.get("country") if country_info else None
        validation_record.card_level_detected = bank_info.get("card_level") if bank_info else None
        validation_record.validation_time_ms = validation_time
        validation_record.api_calls_made = 1
        validation_record.external_services_used = ["validation_service"]
        validation_record.ip_address = request.client.host if request.client else "unknown"
        validation_record.user_agent = request.headers.get("user-agent", "unknown")
        
        # Calculate overall score and update status
        validation_record.calculate_overall_score()
        validation_record.update_validation_status()
        
        db.add(validation_record)
        db.commit()
        
        log_security_event("card_validated", {
            "user_id": current_user.id,
            "card_type": validation_result.get("card_type", "unknown"),
            "is_valid": validation_result["overall_valid"],
            "validation_score": validation_result["score"],
            "validation_time_ms": validation_time,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return ValidationResponse(
            card_number=validation_data.card_number,
            card_type=validation_result.get("card_type", "unknown"),
            is_valid=validation_result["overall_valid"],
            validation_status=validation_record.validation_status.value,
            overall_score=validation_record.overall_score,
            validation_details=validation_record.validation_details,
            validation_errors=validation_record.validation_errors,
            validation_warnings=validation_record.validation_warnings,
            bank_info=bank_info,
            country_info=country_info,
            validation_time_ms=validation_time,
            api_calls_made=validation_record.api_calls_made,
            external_services_used=validation_record.external_services_used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating card: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Card validation failed")

@router.post("/batch", response_model=BatchValidationResponse)
@rate_limit("validation")
async def batch_validate_cards(
    batch_data: BatchValidationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BatchValidationResponse:
    """Validate multiple cards in batch."""
    try:
        start_time = time.time()
        
        results = []
        successful_validations = 0
        failed_validations = 0
        errors = []
        warnings = []
        
        for card_data in batch_data.cards:
            try:
                # Validate card number
                card_number = card_data.get("card_number", "")
                card_validation = validate_input(card_number, "card_number")
                if not card_validation["is_valid"]:
                    errors.append(f"Invalid card number: {card_number}")
                    failed_validations += 1
                    continue
                
                # Perform validation
                validation_result = comprehensive_card_validation(
                    card_number,
                    card_data.get("expiry_date", ""),
                    card_data.get("cvv", ""),
                    card_data.get("cardholder_name", "")
                )
                
                # Get additional information if requested
                bank_info = None
                country_info = None
                
                if batch_data.include_bank_info and validation_result["card_type"] != "unknown":
                    bank_info = {
                        "bank_name": "Sample Bank",
                        "card_level": "Standard",
                        "country": "US"
                    }
                
                if batch_data.include_country_info:
                    country_info = {
                        "country": "United States",
                        "currency": "USD",
                        "region": "North America"
                    }
                
                # Create validation response
                validation_response = ValidationResponse(
                    card_number=card_number,
                    card_type=validation_result.get("card_type", "unknown"),
                    is_valid=validation_result["overall_valid"],
                    validation_status="passed" if validation_result["overall_valid"] else "failed",
                    overall_score=validation_result["score"],
                    validation_details={
                        "luhn_check": {"passed": validation_result.get("card_number_valid", False)},
                        "expiry_check": {"passed": validation_result.get("expiry_valid", False)},
                        "cvv_check": {"passed": validation_result.get("cvv_valid", False)}
                    },
                    validation_errors=validation_result.get("errors", []),
                    validation_warnings=validation_result.get("warnings", []),
                    bank_info=bank_info,
                    country_info=country_info,
                    validation_time_ms=0,
                    api_calls_made=1,
                    external_services_used=["validation_service"]
                )
                
                results.append(validation_response)
                
                if validation_result["overall_valid"]:
                    successful_validations += 1
                else:
                    failed_validations += 1
                
                warnings.extend(validation_result.get("warnings", []))
                
            except Exception as e:
                errors.append(f"Error validating card {card_data.get('card_number', 'unknown')}: {str(e)}")
                failed_validations += 1
        
        processing_time = int((time.time() - start_time) * 1000)
        average_score = sum(r.overall_score for r in results) / len(results) if results else 0
        
        log_security_event("batch_validation_completed", {
            "user_id": current_user.id,
            "total_cards": len(batch_data.cards),
            "successful_validations": successful_validations,
            "failed_validations": failed_validations,
            "average_score": average_score,
            "processing_time_ms": processing_time,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return BatchValidationResponse(
            total_cards=len(batch_data.cards),
            processed_cards=len(results),
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            average_score=average_score,
            processing_time_ms=processing_time,
            results=results,
            errors=errors,
            warnings=list(set(warnings))  # Remove duplicates
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch validation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Batch validation failed")

@router.get("/results", response_model=ValidationResultListResponse)
async def get_validation_results(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    validation_type: Optional[ValidationType] = Query(None),
    validation_status: Optional[ValidationStatus] = Query(None),
    is_valid: Optional[bool] = Query(None),
    card_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of validation results."""
    try:
        query = db.query(ValidationResult)
        
        # Users can only see their own validation results unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ValidationResult.user_id == current_user.id)
        
        # Apply filters
        if validation_type:
            query = query.filter(ValidationResult.validation_type == validation_type)
        if validation_status:
            query = query.filter(ValidationResult.validation_status == validation_status)
        if is_valid is not None:
            query = query.filter(ValidationResult.is_valid == is_valid)
        if card_type:
            query = query.filter(ValidationResult.card_type_detected == card_type)
        
        # Date range filter
        if date_from:
            from datetime import datetime
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(ValidationResult.created_at >= date_from_obj)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from format")
        
        if date_to:
            from datetime import datetime
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(ValidationResult.created_at <= date_to_obj)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to format")
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        results = query.order_by(desc(ValidationResult.created_at)).offset((page - 1) * size).limit(size).all()
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        # Calculate stats
        stats = {
            "total_validations": total,
            "successful_validations": db.query(ValidationResult).filter(ValidationResult.is_valid == True).count(),
            "failed_validations": db.query(ValidationResult).filter(ValidationResult.is_valid == False).count(),
            "average_score": db.query(ValidationResult.overall_score).filter(ValidationResult.overall_score > 0).scalar() or 0
        }
        
        return {
            "results": [ValidationResultResponse.from_orm(result) for result in results],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation results: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve validation results")

@router.get("/results/{result_id}", response_model=ValidationResultResponse)
async def get_validation_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ValidationResultResponse:
    """Get validation result by ID."""
    try:
        query = db.query(ValidationResult).filter(ValidationResult.id == result_id)
        
        # Users can only see their own validation results unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ValidationResult.user_id == current_user.id)
        
        result = query.first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation result not found")
        
        return ValidationResultResponse.from_orm(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation result {result_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve validation result")

@router.get("/stats", response_model=ValidationStats)
async def get_validation_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ValidationStats:
    """Get validation statistics."""
    try:
        query = db.query(ValidationResult)
        
        # Users can only see their own stats unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ValidationResult.user_id == current_user.id)
        
        total_validations = query.count()
        successful_validations = query.filter(ValidationResult.is_valid == True).count()
        failed_validations = query.filter(ValidationResult.is_valid == False).count()
        
        # Calculate average score
        avg_score_result = db.query(ValidationResult.overall_score).filter(ValidationResult.overall_score > 0).scalar()
        average_score = float(avg_score_result) if avg_score_result else 0.0
        
        # Calculate average validation time
        avg_time_result = db.query(ValidationResult.validation_time_ms).filter(ValidationResult.validation_time_ms > 0).scalar()
        average_validation_time = float(avg_time_result) if avg_time_result else 0.0
        
        # Get most common card type
        from sqlalchemy import func
        card_type_result = db.query(
            ValidationResult.card_type_detected,
            func.count(ValidationResult.id).label('count')
        ).filter(ValidationResult.card_type_detected.isnot(None)).group_by(
            ValidationResult.card_type_detected
        ).order_by(func.count(ValidationResult.id).desc()).first()
        
        most_common_card_type = card_type_result[0] if card_type_result else "unknown"
        
        # Get most common bank
        bank_result = db.query(
            ValidationResult.bank_name_detected,
            func.count(ValidationResult.id).label('count')
        ).filter(ValidationResult.bank_name_detected.isnot(None)).group_by(
            ValidationResult.bank_name_detected
        ).order_by(func.count(ValidationResult.id).desc()).first()
        
        most_common_bank = bank_result[0] if bank_result else "unknown"
        
        # Calculate success rate
        validation_success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0.0
        
        # Get recent validations
        recent_validations = query.order_by(desc(ValidationResult.created_at)).limit(10).all()
        recent_validations_data = [
            {
                "id": result.id,
                "card_type": result.card_type_detected,
                "is_valid": result.is_valid,
                "score": result.overall_score,
                "created_at": result.created_at.isoformat() if result.created_at else None
            }
            for result in recent_validations
        ]
        
        return ValidationStats(
            total_validations=total_validations,
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            average_score=average_score,
            average_validation_time=average_validation_time,
            most_common_card_type=most_common_card_type,
            most_common_bank=most_common_bank,
            validation_success_rate=validation_success_rate,
            recent_validations=recent_validations_data
        )
    except Exception as e:
        logger.error(f"Error getting validation stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve validation statistics")

@router.delete("/results/{result_id}")
async def delete_validation_result(
    result_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete validation result."""
    try:
        query = db.query(ValidationResult).filter(ValidationResult.id == result_id)
        
        # Users can only delete their own validation results unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ValidationResult.user_id == current_user.id)
        
        result = query.first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation result not found")
        
        db.delete(result)
        db.commit()
        
        log_security_event("validation_result_deleted", {
            "user_id": current_user.id,
            "result_id": result_id,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": "Validation result deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting validation result {result_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete validation result")