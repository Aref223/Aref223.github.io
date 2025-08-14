"""
Validation utilities for card validation and verification.

This module provides comprehensive validation functions for credit/debit cards,
including Luhn algorithm, expiry date validation, CVV validation, and BIN checking.
"""

import re
import hashlib
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def luhn_check(card_number: str) -> bool:
    """
    Perform Luhn algorithm check on card number.
    
    Args:
        card_number: Card number to validate
        
    Returns:
        bool: True if card number passes Luhn check, False otherwise
    """
    try:
        # Remove spaces and dashes
        card_number = re.sub(r'[\s\-]', '', card_number)
        
        # Check if card number contains only digits
        if not card_number.isdigit():
            return False
        
        # Luhn algorithm implementation
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        
        return checksum % 10 == 0
        
    except Exception as e:
        logger.error(f"Luhn check failed: {e}")
        return False


def validate_card_number(card_number: str) -> Dict[str, any]:
    """
    Comprehensive card number validation.
    
    Args:
        card_number: Card number to validate
        
    Returns:
        dict: Validation results including validity, card type, and details
    """
    result = {
        "is_valid": False,
        "card_type": "unknown",
        "length": 0,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Remove spaces and dashes
        clean_number = re.sub(r'[\s\-]', '', card_number)
        
        # Check length
        result["length"] = len(clean_number)
        
        if result["length"] < 13 or result["length"] > 19:
            result["errors"].append("Invalid card number length")
            return result
        
        # Check if contains only digits
        if not clean_number.isdigit():
            result["errors"].append("Card number must contain only digits")
            return result
        
        # Perform Luhn check
        if not luhn_check(clean_number):
            result["errors"].append("Card number failed Luhn algorithm check")
            return result
        
        # Detect card type
        card_type = detect_card_type(clean_number)
        result["card_type"] = card_type
        
        # Additional validations based on card type
        if card_type == "visa":
            if not clean_number.startswith("4"):
                result["warnings"].append("Visa cards should start with 4")
        elif card_type == "mastercard":
            if not (clean_number.startswith("5") and clean_number[1] in "12345"):
                result["warnings"].append("Mastercard should start with 51-55")
        elif card_type == "amex":
            if not clean_number.startswith(("34", "37")):
                result["warnings"].append("American Express should start with 34 or 37")
        
        # If no errors, card is valid
        if not result["errors"]:
            result["is_valid"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Card number validation failed: {e}")
        result["errors"].append(f"Validation error: {str(e)}")
        return result


def detect_card_type(card_number: str) -> str:
    """
    Detect card type based on card number patterns.
    
    Args:
        card_number: Card number to analyze
        
    Returns:
        str: Detected card type
    """
    # Remove spaces and dashes
    clean_number = re.sub(r'[\s\-]', '', card_number)
    
    # Visa: starts with 4, length 13, 16, or 19
    if clean_number.startswith("4") and len(clean_number) in [13, 16, 19]:
        return "visa"
    
    # Mastercard: starts with 51-55 or 2221-2720, length 16
    if len(clean_number) == 16:
        if clean_number.startswith(("51", "52", "53", "54", "55")):
            return "mastercard"
        if clean_number.startswith("2") and 2221 <= int(clean_number[:4]) <= 2720:
            return "mastercard"
    
    # American Express: starts with 34 or 37, length 15
    if clean_number.startswith(("34", "37")) and len(clean_number) == 15:
        return "amex"
    
    # Discover: starts with 6011, 622126-622925, 644-649, 65, length 16
    if len(clean_number) == 16:
        if clean_number.startswith("6011"):
            return "discover"
        if clean_number.startswith("622") and 622126 <= int(clean_number[:6]) <= 622925:
            return "discover"
        if clean_number.startswith(("644", "645", "646", "647", "648", "649")):
            return "discover"
        if clean_number.startswith("65"):
            return "discover"
    
    # JCB: starts with 2131, 1800, 35, length 16
    if len(clean_number) == 16:
        if clean_number.startswith(("2131", "1800", "35")):
            return "jcb"
    
    return "unknown"


def validate_expiry_date(expiry_date: str) -> Dict[str, any]:
    """
    Validate card expiry date.
    
    Args:
        expiry_date: Expiry date in MM/YY or MM/YYYY format
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "is_expired": False,
        "month": 0,
        "year": 0,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Parse expiry date
        if "/" not in expiry_date:
            result["errors"].append("Invalid expiry date format. Use MM/YY or MM/YYYY")
            return result
        
        month_str, year_str = expiry_date.split("/")
        
        # Validate month
        try:
            month = int(month_str)
            if month < 1 or month > 12:
                result["errors"].append("Invalid month. Must be between 01 and 12")
                return result
            result["month"] = month
        except ValueError:
            result["errors"].append("Invalid month format")
            return result
        
        # Validate year
        try:
            year = int(year_str)
            if len(year_str) == 2:
                # Convert 2-digit year to 4-digit
                year += 2000
            elif len(year_str) != 4:
                result["errors"].append("Invalid year format. Use YY or YYYY")
                return result
            
            result["year"] = year
        except ValueError:
            result["errors"].append("Invalid year format")
            return result
        
        # Check if expired
        current_date = date.today()
        expiry_date_obj = date(year, month, 1)
        
        # Set to last day of the month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        expiry_date_obj = next_month - date.timedelta(days=1)
        
        if expiry_date_obj < current_date:
            result["is_expired"] = True
            result["errors"].append("Card has expired")
        
        # Check if too far in future (more than 10 years)
        if year > current_date.year + 10:
            result["warnings"].append("Expiry date is more than 10 years in the future")
        
        # If no errors, date is valid
        if not result["errors"]:
            result["is_valid"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Expiry date validation failed: {e}")
        result["errors"].append(f"Validation error: {str(e)}")
        return result


def validate_cvv(cvv: str, card_type: str) -> Dict[str, any]:
    """
    Validate CVV code.
    
    Args:
        cvv: CVV code to validate
        card_type: Type of card (visa, mastercard, amex, etc.)
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "expected_length": 0,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Remove spaces
        clean_cvv = re.sub(r'\s', '', cvv)
        
        # Check if contains only digits
        if not clean_cvv.isdigit():
            result["errors"].append("CVV must contain only digits")
            return result
        
        # Set expected length based on card type
        if card_type == "amex":
            expected_length = 4
        else:
            expected_length = 3
        
        result["expected_length"] = expected_length
        
        # Check length
        if len(clean_cvv) != expected_length:
            result["errors"].append(f"CVV should be {expected_length} digits for {card_type}")
            return result
        
        # Check for common invalid patterns
        if clean_cvv == "000":
            result["warnings"].append("CVV should not be all zeros")
        
        if clean_cvv == "123":
            result["warnings"].append("CVV should not be sequential numbers")
        
        # If no errors, CVV is valid
        if not result["errors"]:
            result["is_valid"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"CVV validation failed: {e}")
        result["errors"].append(f"Validation error: {str(e)}")
        return result


def hash_card_number(card_number: str) -> str:
    """
    Create a secure hash of card number for storage.
    
    Args:
        card_number: Card number to hash
        
    Returns:
        str: SHA-256 hash of the card number
    """
    # Remove spaces and dashes
    clean_number = re.sub(r'[\s\-]', '', card_number)
    
    # Create hash
    return hashlib.sha256(clean_number.encode()).hexdigest()


def validate_cardholder_name(name: str) -> Dict[str, any]:
    """
    Validate cardholder name.
    
    Args:
        name: Cardholder name to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check if name is provided
        if not name or not name.strip():
            result["errors"].append("Cardholder name is required")
            return result
        
        # Remove extra whitespace
        clean_name = " ".join(name.split())
        
        # Check length
        if len(clean_name) < 2:
            result["errors"].append("Cardholder name is too short")
            return result
        
        if len(clean_name) > 50:
            result["warnings"].append("Cardholder name is very long")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", clean_name):
            result["errors"].append("Cardholder name contains invalid characters")
            return result
        
        # Check for common invalid patterns
        if clean_name.lower() in ["test", "example", "sample", "demo"]:
            result["warnings"].append("Cardholder name appears to be a test value")
        
        # If no errors, name is valid
        if not result["errors"]:
            result["is_valid"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Cardholder name validation failed: {e}")
        result["errors"].append(f"Validation error: {str(e)}")
        return result


def comprehensive_card_validation(
    card_number: str,
    expiry_date: str,
    cvv: str,
    cardholder_name: Optional[str] = None
) -> Dict[str, any]:
    """
    Perform comprehensive card validation.
    
    Args:
        card_number: Card number to validate
        expiry_date: Expiry date
        cvv: CVV code
        cardholder_name: Cardholder name (optional)
        
    Returns:
        dict: Comprehensive validation results
    """
    result = {
        "overall_valid": False,
        "card_number_valid": False,
        "expiry_valid": False,
        "cvv_valid": False,
        "cardholder_valid": True,  # Default to True if not provided
        "card_type": "unknown",
        "score": 0,
        "errors": [],
        "warnings": []
    }
    
    # Validate card number
    card_validation = validate_card_number(card_number)
    result["card_number_valid"] = card_validation["is_valid"]
    result["card_type"] = card_validation["card_type"]
    result["errors"].extend(card_validation["errors"])
    result["warnings"].extend(card_validation["warnings"])
    
    # Validate expiry date
    expiry_validation = validate_expiry_date(expiry_date)
    result["expiry_valid"] = expiry_validation["is_valid"]
    result["errors"].extend(expiry_validation["errors"])
    result["warnings"].extend(expiry_validation["warnings"])
    
    # Validate CVV
    cvv_validation = validate_cvv(cvv, result["card_type"])
    result["cvv_valid"] = cvv_validation["is_valid"]
    result["errors"].extend(cvv_validation["errors"])
    result["warnings"].extend(cvv_validation["warnings"])
    
    # Validate cardholder name if provided
    if cardholder_name:
        name_validation = validate_cardholder_name(cardholder_name)
        result["cardholder_valid"] = name_validation["is_valid"]
        result["errors"].extend(name_validation["errors"])
        result["warnings"].extend(name_validation["warnings"])
    
    # Calculate overall score
    score = 0
    if result["card_number_valid"]:
        score += 40
    if result["expiry_valid"]:
        score += 30
    if result["cvv_valid"]:
        score += 20
    if result["cardholder_valid"]:
        score += 10
    
    result["score"] = score
    
    # Determine overall validity
    result["overall_valid"] = (
        result["card_number_valid"] and
        result["expiry_valid"] and
        result["cvv_valid"] and
        result["cardholder_valid"]
    )
    
    return result