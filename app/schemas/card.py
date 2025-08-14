"""
Card data schemas for card operations and validation.

This module contains Pydantic models for card-related requests and responses
including card data creation, updates, validation, and card information retrieval.
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.card_data import CardType, CardStatus

class CardDataBase(BaseModel):
    """Base card data model with common fields."""
    card_type: CardType
    card_status: CardStatus = CardStatus.PENDING
    bank_name: Optional[str] = None
    card_level: Optional[str] = None
    country_issued: Optional[str] = None
    currency: Optional[str] = None
    source_url: Optional[str] = None

    @validator('bank_name', 'card_level', 'country_issued')
    def validate_string_fields(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Field must be at least 2 characters long')
        return v.strip() if v else None

    @validator('currency')
    def validate_currency(cls, v):
        if v is not None and len(v) != 3:
            raise ValueError('Currency code must be 3 characters')
        return v.upper() if v else None

class CardDataCreate(CardDataBase):
    """Request model for card data creation."""
    card_number: str
    expiry_date: Optional[str] = None
    cvv: Optional[str] = None
    cardholder_name: Optional[str] = None

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

    @validator('cardholder_name')
    def validate_cardholder_name(cls, v):
        if v is not None:
            import re
            clean_name = " ".join(v.split())
            if len(clean_name) < 2:
                raise ValueError('Cardholder name must be at least 2 characters')
            if not re.match(r"^[a-zA-Z\s\-']+$", clean_name):
                raise ValueError('Cardholder name contains invalid characters')
        return v

class CardDataUpdate(BaseModel):
    """Request model for card data updates."""
    card_status: Optional[CardStatus] = None
    bank_name: Optional[str] = None
    card_level: Optional[str] = None
    country_issued: Optional[str] = None
    currency: Optional[str] = None
    is_valid: Optional[bool] = None
    validation_score: Optional[int] = None

    @validator('validation_score')
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Validation score must be between 0 and 100')
        return v

class CardDataResponse(BaseModel):
    """Response model for card data information."""
    id: int
    card_type: str
    card_status: str
    is_valid: bool
    validation_score: int
    validation_errors: List[str]
    validation_warnings: List[str]
    bank_name: Optional[str]
    card_level: Optional[str]
    country_issued: Optional[str]
    currency: Optional[str]
    source_url: Optional[str]
    scraped_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class CardDataListResponse(BaseModel):
    """Response model for card data list."""
    cards: List[CardDataResponse]
    total: int
    page: int
    size: int
    pages: int
    stats: Dict[str, Any]

class CardValidationRequest(BaseModel):
    """Request model for card validation."""
    card_number: str
    expiry_date: Optional[str] = None
    cvv: Optional[str] = None
    cardholder_name: Optional[str] = None
    validation_type: str = "comprehensive"

    @validator('card_number')
    def validate_card_number(cls, v):
        import re
        clean_number = re.sub(r'[\s\-]', '', v)
        if not clean_number.isdigit():
            raise ValueError('Card number must contain only digits')
        if len(clean_number) < 13 or len(clean_number) > 19:
            raise ValueError('Card number must be 13-19 digits')
        return clean_number

    @validator('validation_type')
    def validate_validation_type(cls, v):
        allowed_types = ["luhn_check", "expiry_check", "cvv_check", "bin_check", "comprehensive"]
        if v not in allowed_types:
            raise ValueError(f'Validation type must be one of: {", ".join(allowed_types)}')
        return v

class CardValidationResponse(BaseModel):
    """Response model for card validation results."""
    card_number: str
    card_type: str
    is_valid: bool
    validation_score: int
    validation_details: Dict[str, Any]
    validation_errors: List[str]
    validation_warnings: List[str]
    bank_info: Optional[Dict[str, Any]]
    country_info: Optional[Dict[str, Any]]
    validation_time_ms: int

class CardStats(BaseModel):
    """Card statistics model."""
    total_cards: int
    valid_cards: int
    invalid_cards: int
    visa_cards: int
    mastercard_cards: int
    amex_cards: int
    discover_cards: int
    unknown_cards: int
    average_validation_score: float
    recent_scrapes: int

class CardSearchRequest(BaseModel):
    """Request model for card search."""
    card_type: Optional[CardType] = None
    card_status: Optional[CardStatus] = None
    bank_name: Optional[str] = None
    country_issued: Optional[str] = None
    is_valid: Optional[bool] = None
    min_validation_score: Optional[int] = None
    max_validation_score: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    size: int = 20

    @validator('min_validation_score', 'max_validation_score')
    def validate_score_range(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Validation score must be between 0 and 100')
        return v

    @validator('page', 'size')
    def validate_pagination(cls, v):
        if v < 1:
            raise ValueError('Page and size must be greater than 0')
        return v