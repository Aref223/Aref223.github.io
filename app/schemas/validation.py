"""
Validation schemas for card validation operations.

This module contains Pydantic models for validation-related requests and responses
including validation requests, results, and validation history.
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.validation_result import ValidationStatus, ValidationType

class ValidationRequest(BaseModel):
    """Request model for card validation."""
    card_number: str
    expiry_date: Optional[str] = None
    cvv: Optional[str] = None
    cardholder_name: Optional[str] = None
    validation_type: ValidationType = ValidationType.COMPREHENSIVE
    include_bank_info: bool = True
    include_country_info: bool = True

    @validator('card_number')
    def validate_card_number(cls, v):
        import re
        clean_number = re.sub(r'[\s\-]', '', v)
        if not clean_number.isdigit():
            raise ValueError('Card number must contain only digits')
        if len(clean_number) < 13 or len(clean_number) > 19:
            raise ValueError('Card number must be 13-19 digits')
        return clean_number

    @validator('expiry_date')
    def validate_expiry_date(cls, v):
        if v is not None:
            import re
            if not re.match(r'^(0[1-9]|1[0-2])/([0-9]{2}|[0-9]{4})$', v):
                raise ValueError('Expiry date must be in MM/YY or MM/YYYY format')
        return v

    @validator('cvv')
    def validate_cvv(cls, v):
        if v is not None:
            import re
            clean_cvv = re.sub(r'\s', '', v)
            if not clean_cvv.isdigit():
                raise ValueError('CVV must contain only digits')
            if len(clean_cvv) not in [3, 4]:
                raise ValueError('CVV must be 3 or 4 digits')
        return v

class ValidationResponse(BaseModel):
    """Response model for validation results."""
    card_number: str
    card_type: str
    is_valid: bool
    validation_status: str
    overall_score: float
    validation_details: Dict[str, Any]
    validation_errors: List[str]
    validation_warnings: List[str]
    bank_info: Optional[Dict[str, Any]]
    country_info: Optional[Dict[str, Any]]
    validation_time_ms: int
    api_calls_made: int
    external_services_used: List[str]

class ValidationResultResponse(BaseModel):
    """Response model for validation result information."""
    id: int
    validation_type: str
    validation_status: str
    overall_score: float
    is_valid: bool
    luhn_check_passed: Optional[bool]
    expiry_check_passed: Optional[bool]
    cvv_check_passed: Optional[bool]
    bin_check_passed: Optional[bool]
    bank_check_passed: Optional[bool]
    country_check_passed: Optional[bool]
    validation_details: Dict[str, Any]
    validation_errors: List[str]
    validation_warnings: List[str]
    card_number_length: Optional[int]
    card_type_detected: Optional[str]
    bank_name_detected: Optional[str]
    country_detected: Optional[str]
    card_level_detected: Optional[str]
    validation_time_ms: Optional[int]
    api_calls_made: int
    external_services_used: List[str]
    validation_source: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ValidationResultListResponse(BaseModel):
    """Response model for validation result list."""
    results: List[ValidationResultResponse]
    total: int
    page: int
    size: int
    pages: int
    stats: Dict[str, Any]

class ValidationStats(BaseModel):
    """Validation statistics model."""
    total_validations: int
    successful_validations: int
    failed_validations: int
    average_score: float
    average_validation_time: float
    most_common_card_type: str
    most_common_bank: str
    validation_success_rate: float
    recent_validations: List[Dict[str, Any]]

class ValidationSearchRequest(BaseModel):
    """Request model for validation result search."""
    validation_type: Optional[ValidationType] = None
    validation_status: Optional[ValidationStatus] = None
    is_valid: Optional[bool] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    card_type: Optional[str] = None
    bank_name: Optional[str] = None
    country: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    size: int = 20

    @validator('min_score', 'max_score')
    def validate_score_range(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v

    @validator('page', 'size')
    def validate_pagination(cls, v):
        if v < 1:
            raise ValueError('Page and size must be greater than 0')
        return v

class BatchValidationRequest(BaseModel):
    """Request model for batch validation."""
    cards: List[Dict[str, Any]]
    validation_type: ValidationType = ValidationType.COMPREHENSIVE
    include_bank_info: bool = True
    include_country_info: bool = True
    max_concurrent: int = 5

    @validator('cards')
    def validate_cards(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one card is required')
        if len(v) > 100:
            raise ValueError('Maximum 100 cards allowed per batch')
        return v

    @validator('max_concurrent')
    def validate_max_concurrent(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Max concurrent must be between 1 and 20')
        return v

class BatchValidationResponse(BaseModel):
    """Response model for batch validation results."""
    total_cards: int
    processed_cards: int
    successful_validations: int
    failed_validations: int
    average_score: float
    processing_time_ms: int
    results: List[ValidationResponse]
    errors: List[str]
    warnings: List[str]

class ValidationHistoryRequest(BaseModel):
    """Request model for validation history."""
    card_number_hash: Optional[str] = None
    card_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    size: int = 20

    @validator('page', 'size')
    def validate_pagination(cls, v):
        if v < 1:
            raise ValueError('Page and size must be greater than 0')
        return v