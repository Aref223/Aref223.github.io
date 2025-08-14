"""
Validation result model for storing card validation results and audit trail.

This module defines the ValidationResult model for tracking validation operations,
including detailed validation checks, scores, and comprehensive audit information.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, JSON, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from typing import Optional, Dict, Any

from app.database import Base


class ValidationStatus(str, enum.Enum):
    """Validation status enumeration."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error"


class ValidationType(str, enum.Enum):
    """Validation type enumeration."""
    LUHN_CHECK = "luhn_check"
    EXPIRY_CHECK = "expiry_check"
    CVV_CHECK = "cvv_check"
    BIN_CHECK = "bin_check"
    BANK_CHECK = "bank_check"
    COUNTRY_CHECK = "country_check"
    COMPREHENSIVE = "comprehensive"


class ValidationResult(Base):
    """
    Validation result model for storing card validation results and audit trail.
    
    This model includes detailed validation checks, scoring, and comprehensive
    audit information for tracking validation operations.
    """
    
    __tablename__ = "validation_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_data_id = Column(Integer, ForeignKey("card_data.id"), nullable=False)
    
    # Validation identification
    validation_type = Column(Enum(ValidationType), nullable=False)
    validation_status = Column(Enum(ValidationStatus), nullable=False)
    
    # Validation results
    overall_score = Column(Float, default=0.0)  # 0.0 to 100.0
    is_valid = Column(Boolean, default=False)
    
    # Detailed validation checks
    luhn_check_passed = Column(Boolean)
    expiry_check_passed = Column(Boolean)
    cvv_check_passed = Column(Boolean)
    bin_check_passed = Column(Boolean)
    bank_check_passed = Column(Boolean)
    country_check_passed = Column(Boolean)
    
    # Validation details
    validation_details = Column(JSON, default=dict)  # Detailed results for each check
    validation_errors = Column(JSON, default=list)  # List of validation errors
    validation_warnings = Column(JSON, default=list)  # List of validation warnings
    
    # Card information (encrypted)
    card_number_length = Column(Integer)
    card_type_detected = Column(String(50))
    bank_name_detected = Column(String(200))
    country_detected = Column(String(100))
    card_level_detected = Column(String(50))
    
    # Performance metrics
    validation_time_ms = Column(Integer)
    api_calls_made = Column(Integer, default=0)
    external_services_used = Column(JSON, default=list)
    
    # Security and audit
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(255))
    validation_source = Column(String(100))  # "manual", "batch", "api"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="validation_results")
    card_data = relationship("CardData", back_populates="validation_results")
    
    def __repr__(self):
        return f"<ValidationResult(id={self.id}, type='{self.validation_type}', status='{self.validation_status}')>"
    
    @property
    def passed_checks_count(self) -> int:
        """Count the number of passed validation checks."""
        checks = [
            self.luhn_check_passed,
            self.expiry_check_passed,
            self.cvv_check_passed,
            self.bin_check_passed,
            self.bank_check_passed,
            self.country_check_passed
        ]
        return sum(1 for check in checks if check is True)
    
    @property
    def total_checks_count(self) -> int:
        """Count the total number of validation checks performed."""
        checks = [
            self.luhn_check_passed,
            self.expiry_check_passed,
            self.cvv_check_passed,
            self.bin_check_passed,
            self.bank_check_passed,
            self.country_check_passed
        ]
        return sum(1 for check in checks if check is not None)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of validation checks."""
        total = self.total_checks_count
        if total == 0:
            return 0.0
        return (self.passed_checks_count / total) * 100
    
    def update_validation_status(self) -> None:
        """Update validation status based on check results."""
        if self.overall_score >= 90:
            self.validation_status = ValidationStatus.PASSED
            self.is_valid = True
        elif self.overall_score >= 70:
            self.validation_status = ValidationStatus.PARTIAL
            self.is_valid = False
        else:
            self.validation_status = ValidationStatus.FAILED
            self.is_valid = False
    
    def add_validation_error(self, error: str) -> None:
        """
        Add a validation error.
        
        Args:
            error: Error message to add
        """
        if not self.validation_errors:
            self.validation_errors = []
        self.validation_errors.append(error)
    
    def add_validation_warning(self, warning: str) -> None:
        """
        Add a validation warning.
        
        Args:
            warning: Warning message to add
        """
        if not self.validation_warnings:
            self.validation_warnings = []
        self.validation_warnings.append(warning)
    
    def set_check_result(self, check_name: str, passed: bool, details: dict = None) -> None:
        """
        Set the result of a specific validation check.
        
        Args:
            check_name: Name of the validation check
            passed: Whether the check passed
            details: Additional details about the check
        """
        if check_name == "luhn_check":
            self.luhn_check_passed = passed
        elif check_name == "expiry_check":
            self.expiry_check_passed = passed
        elif check_name == "cvv_check":
            self.cvv_check_passed = passed
        elif check_name == "bin_check":
            self.bin_check_passed = passed
        elif check_name == "bank_check":
            self.bank_check_passed = passed
        elif check_name == "country_check":
            self.country_check_passed = passed
        
        # Update validation details
        if not self.validation_details:
            self.validation_details = {}
        self.validation_details[check_name] = {
            "passed": passed,
            "details": details or {}
        }
    
    def calculate_overall_score(self) -> float:
        """
        Calculate overall validation score based on individual checks.
        
        Returns:
            float: Overall score (0.0 to 100.0)
        """
        weights = {
            "luhn_check": 25.0,
            "expiry_check": 20.0,
            "cvv_check": 15.0,
            "bin_check": 20.0,
            "bank_check": 10.0,
            "country_check": 10.0
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for check_name, weight in weights.items():
            check_result = self.validation_details.get(check_name, {})
            if check_result.get("passed") is True:
                total_score += weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        self.overall_score = (total_score / total_weight) * 100
        return self.overall_score
    
    def add_external_service(self, service_name: str) -> None:
        """
        Add an external service used during validation.
        
        Args:
            service_name: Name of the external service
        """
        if not self.external_services_used:
            self.external_services_used = []
        if service_name not in self.external_services_used:
            self.external_services_used.append(service_name)
    
    def increment_api_calls(self) -> None:
        """Increment the API calls counter."""
        self.api_calls_made += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert validation result to dictionary representation.
        
        Returns:
            dict: Validation result as dictionary
        """
        return {
            "id": self.id,
            "validation_type": self.validation_type.value,
            "validation_status": self.validation_status.value,
            "overall_score": self.overall_score,
            "is_valid": self.is_valid,
            "passed_checks_count": self.passed_checks_count,
            "total_checks_count": self.total_checks_count,
            "success_rate": self.success_rate,
            "validation_details": self.validation_details,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "card_number_length": self.card_number_length,
            "card_type_detected": self.card_type_detected,
            "bank_name_detected": self.bank_name_detected,
            "country_detected": self.country_detected,
            "card_level_detected": self.card_level_detected,
            "validation_time_ms": self.validation_time_ms,
            "api_calls_made": self.api_calls_made,
            "external_services_used": self.external_services_used,
            "validation_source": self.validation_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_validation_result(
        cls,
        user_id: int,
        card_data_id: int,
        validation_type: ValidationType,
        validation_source: str = "manual",
        **kwargs
    ) -> "ValidationResult":
        """
        Create a new validation result.
        
        Args:
            user_id: ID of the user performing validation
            card_data_id: ID of the card data being validated
            validation_type: Type of validation to perform
            validation_source: Source of the validation request
            **kwargs: Additional validation attributes
            
        Returns:
            ValidationResult: Newly created validation result instance
        """
        return cls(
            user_id=user_id,
            card_data_id=card_data_id,
            validation_type=validation_type,
            validation_source=validation_source,
            validation_status=ValidationStatus.FAILED,  # Default status
            **kwargs
        )