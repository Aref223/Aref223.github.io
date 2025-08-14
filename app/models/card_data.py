"""
Card data model for storing scraped visa and debit card information.

This module defines the CardData model with encrypted storage for sensitive
card information and comprehensive metadata tracking.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from typing import Optional, Dict, Any

from app.database import Base
from app.utils.encryption import encrypt_data, decrypt_data


class CardType(str, enum.Enum):
    """Card type enumeration."""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    UNKNOWN = "unknown"


class CardStatus(str, enum.Enum):
    """Card status enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    PENDING = "pending"


class CardData(Base):
    """
    Card data model for storing scraped visa and debit card information.
    
    This model includes encrypted storage for sensitive card data,
    comprehensive validation results, and detailed metadata tracking.
    """
    
    __tablename__ = "card_data"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scraping_job_id = Column(Integer, ForeignKey("scraping_jobs.id"), nullable=True)
    
    # Card identification
    card_number_hash = Column(String(255), index=True, nullable=False)  # SHA-256 hash
    card_type = Column(Enum(CardType), nullable=False)
    card_status = Column(Enum(CardStatus), default=CardStatus.PENDING, nullable=False)
    
    # Encrypted sensitive data
    encrypted_card_number = Column(Text, nullable=False)
    encrypted_expiry_date = Column(Text, nullable=True)
    encrypted_cvv = Column(Text, nullable=True)
    encrypted_cardholder_name = Column(Text, nullable=True)
    
    # Validation and metadata
    is_valid = Column(Boolean, default=False)
    validation_score = Column(Integer, default=0)  # 0-100
    validation_errors = Column(JSON, default=list)
    validation_warnings = Column(JSON, default=list)
    
    # Additional card information
    bank_name = Column(String(200))
    card_level = Column(String(50))  # Classic, Gold, Platinum, etc.
    country_issued = Column(String(100))
    currency = Column(String(10))
    
    # Scraping metadata
    source_url = Column(String(500))
    scraped_at = Column(DateTime(timezone=True), default=func.now())
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Processing metadata
    processing_time_ms = Column(Integer)
    retry_count = Column(Integer, default=0)
    last_validation_attempt = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="card_data")
    scraping_job = relationship("ScrapingJob", back_populates="card_data")
    validation_results = relationship("ValidationResult", back_populates="card_data")
    
    def __repr__(self):
        return f"<CardData(id={self.id}, card_type='{self.card_type}', status='{self.card_status}')>"
    
    def set_card_number(self, card_number: str) -> None:
        """
        Set and encrypt card number.
        
        Args:
            card_number: Plain text card number
        """
        from app.utils.validation import hash_card_number
        self.card_number_hash = hash_card_number(card_number)
        self.encrypted_card_number = encrypt_data(card_number)
    
    def get_card_number(self) -> Optional[str]:
        """
        Decrypt and return card number.
        
        Returns:
            str: Decrypted card number or None if decryption fails
        """
        try:
            return decrypt_data(self.encrypted_card_number)
        except Exception:
            return None
    
    def set_expiry_date(self, expiry_date: str) -> None:
        """
        Set and encrypt expiry date.
        
        Args:
            expiry_date: Card expiry date (MM/YY format)
        """
        self.encrypted_expiry_date = encrypt_data(expiry_date)
    
    def get_expiry_date(self) -> Optional[str]:
        """
        Decrypt and return expiry date.
        
        Returns:
            str: Decrypted expiry date or None if decryption fails
        """
        try:
            return decrypt_data(self.encrypted_expiry_date)
        except Exception:
            return None
    
    def set_cvv(self, cvv: str) -> None:
        """
        Set and encrypt CVV.
        
        Args:
            cvv: Card CVV code
        """
        self.encrypted_cvv = encrypt_data(cvv)
    
    def get_cvv(self) -> Optional[str]:
        """
        Decrypt and return CVV.
        
        Returns:
            str: Decrypted CVV or None if decryption fails
        """
        try:
            return decrypt_data(self.encrypted_cvv)
        except Exception:
            return None
    
    def set_cardholder_name(self, name: str) -> None:
        """
        Set and encrypt cardholder name.
        
        Args:
            name: Cardholder name
        """
        self.encrypted_cardholder_name = encrypt_data(name)
    
    def get_cardholder_name(self) -> Optional[str]:
        """
        Decrypt and return cardholder name.
        
        Returns:
            str: Decrypted cardholder name or None if decryption fails
        """
        try:
            return decrypt_data(self.encrypted_cardholder_name)
        except Exception:
            return None
    
    def update_validation_status(self, is_valid: bool, score: int = 0, errors: list = None, warnings: list = None) -> None:
        """
        Update card validation status and results.
        
        Args:
            is_valid: Whether the card is valid
            score: Validation score (0-100)
            errors: List of validation errors
            warnings: List of validation warnings
        """
        self.is_valid = is_valid
        self.validation_score = max(0, min(100, score))
        self.validation_errors = errors or []
        self.validation_warnings = warnings or []
        self.last_validation_attempt = datetime.utcnow()
        
        # Update card status based on validation
        if is_valid:
            self.card_status = CardStatus.VALID
        else:
            self.card_status = CardStatus.INVALID
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert card data to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive data (admin only)
            
        Returns:
            dict: Card data as dictionary
        """
        data = {
            "id": self.id,
            "card_type": self.card_type.value,
            "card_status": self.card_status.value,
            "is_valid": self.is_valid,
            "validation_score": self.validation_score,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "bank_name": self.bank_name,
            "card_level": self.card_level,
            "country_issued": self.country_issued,
            "currency": self.currency,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data.update({
                "card_number": self.get_card_number(),
                "expiry_date": self.get_expiry_date(),
                "cvv": self.get_cvv(),
                "cardholder_name": self.get_cardholder_name()
            })
        
        return data
    
    @classmethod
    def create_card_data(
        cls,
        user_id: int,
        card_number: str,
        card_type: CardType,
        expiry_date: Optional[str] = None,
        cvv: Optional[str] = None,
        cardholder_name: Optional[str] = None,
        **kwargs
    ) -> "CardData":
        """
        Create a new card data record with proper encryption.
        
        Args:
            user_id: ID of the user who owns this card data
            card_number: Plain text card number
            card_type: Type of card
            expiry_date: Card expiry date
            cvv: Card CVV
            cardholder_name: Cardholder name
            **kwargs: Additional card attributes
            
        Returns:
            CardData: Newly created card data instance
        """
        card_data = cls(
            user_id=user_id,
            card_type=card_type,
            **kwargs
        )
        
        # Set encrypted sensitive data
        card_data.set_card_number(card_number)
        if expiry_date:
            card_data.set_expiry_date(expiry_date)
        if cvv:
            card_data.set_cvv(cvv)
        if cardholder_name:
            card_data.set_cardholder_name(cardholder_name)
        
        return card_data