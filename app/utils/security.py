"""
Security utilities for input validation, rate limiting, and security measures.

This module provides comprehensive security functions including input validation,
rate limiting, sanitization, and other security measures for the application.
"""

import re
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from datetime import datetime, timedelta
import ipaddress
from urllib.parse import urlparse
import json

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API endpoints and user actions.
    
    This class provides rate limiting functionality with configurable
    limits and time windows for different types of operations.
    """
    
    def __init__(self):
        """Initialize rate limiter with empty storage."""
        self.requests = {}
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 100 requests per hour
            "scraping": {"requests": 10, "window": 3600},  # 10 scraping requests per hour
            "validation": {"requests": 50, "window": 3600},  # 50 validations per hour
            "login": {"requests": 5, "window": 300},  # 5 login attempts per 5 minutes
        }
    
    def is_allowed(self, identifier: str, action_type: str = "default") -> bool:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            action_type: Type of action for rate limiting
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        now = time.time()
        limit_config = self.limits.get(action_type, self.limits["default"])
        
        # Get or create request history for identifier
        if identifier not in self.requests:
            self.requests[identifier] = {}
        
        if action_type not in self.requests[identifier]:
            self.requests[identifier][action_type] = []
        
        # Clean old requests outside the time window
        window_start = now - limit_config["window"]
        self.requests[identifier][action_type] = [
            req_time for req_time in self.requests[identifier][action_type]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier][action_type]) >= limit_config["requests"]:
            return False
        
        # Add current request
        self.requests[identifier][action_type].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, action_type: str = "default") -> int:
        """
        Get remaining requests for an identifier.
        
        Args:
            identifier: Unique identifier
            action_type: Type of action
            
        Returns:
            int: Number of remaining requests
        """
        now = time.time()
        limit_config = self.limits.get(action_type, self.limits["default"])
        
        if identifier not in self.requests or action_type not in self.requests[identifier]:
            return limit_config["requests"]
        
        window_start = now - limit_config["window"]
        recent_requests = [
            req_time for req_time in self.requests[identifier][action_type]
            if req_time > window_start
        ]
        
        return max(0, limit_config["requests"] - len(recent_requests))


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(action_type: str = "default"):
    """
    Decorator for rate limiting API endpoints.
    
    Args:
        action_type: Type of action for rate limiting
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract identifier from request (IP address or user ID)
            request = kwargs.get('request') or args[0] if args else None
            if request:
                identifier = get_client_ip(request)
            else:
                identifier = "unknown"
            
            if not rate_limiter.is_allowed(identifier, action_type):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "action_type": action_type,
                        "remaining_requests": rate_limiter.get_remaining_requests(identifier, action_type)
                    }
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_input(data: Any, input_type: str = "general") -> Dict[str, Any]:
    """
    Validate and sanitize input data.
    
    Args:
        data: Data to validate
        input_type: Type of input for specific validation rules
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": True,
        "sanitized_data": data,
        "errors": [],
        "warnings": []
    }
    
    try:
        if input_type == "url":
            result = validate_url(data)
        elif input_type == "email":
            result = validate_email(data)
        elif input_type == "phone":
            result = validate_phone(data)
        elif input_type == "card_number":
            result = validate_card_number_input(data)
        elif input_type == "json":
            result = validate_json(data)
        else:
            result = validate_general_input(data)
        
        return result
        
    except Exception as e:
        logger.error(f"Input validation error: {e}")
        result["is_valid"] = False
        result["errors"].append(f"Validation error: {str(e)}")
        return result


def validate_general_input(data: Any) -> Dict[str, Any]:
    """
    Validate general input data.
    
    Args:
        data: Data to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": True,
        "sanitized_data": data,
        "errors": [],
        "warnings": []
    }
    
    if data is None:
        result["is_valid"] = False
        result["errors"].append("Input cannot be null")
        return result
    
    if isinstance(data, str):
        # Check for SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|/\*|\*/|xp_|sp_)",
            r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                result["is_valid"] = False
                result["errors"].append("Potential SQL injection detected")
                break
        
        # Check for XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                result["is_valid"] = False
                result["errors"].append("Potential XSS attack detected")
                break
        
        # Sanitize string
        if result["is_valid"]:
            result["sanitized_data"] = sanitize_string(data)
    
    return result


def validate_url(url: str) -> Dict[str, Any]:
    """
    Validate URL format and security.
    
    Args:
        url: URL to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "sanitized_data": url,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Parse URL
        parsed = urlparse(url)
        
        # Check if URL has scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            result["errors"].append("Invalid URL format")
            return result
        
        # Check for allowed schemes
        allowed_schemes = ["http", "https"]
        if parsed.scheme not in allowed_schemes:
            result["errors"].append(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
            return result
        
        # Check for private/local IP addresses
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback:
                result["errors"].append("URL cannot point to private or local IP address")
                return result
        except ValueError:
            # Not an IP address, continue with hostname validation
            pass
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"\.(exe|bat|cmd|com|pif|scr|vbs)$",
            r"javascript:",
            r"data:",
            r"file:",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                result["errors"].append("URL contains suspicious content")
                return result
        
        result["is_valid"] = True
        return result
        
    except Exception as e:
        result["errors"].append(f"URL validation error: {str(e)}")
        return result


def validate_email(email: str) -> Dict[str, Any]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "sanitized_data": email,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Basic email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            result["errors"].append("Invalid email format")
            return result
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"\.(exe|bat|cmd|com|pif|scr|vbs)$",
            r"javascript:",
            r"<script",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                result["errors"].append("Email contains suspicious content")
                return result
        
        # Check length
        if len(email) > 254:
            result["errors"].append("Email address too long")
            return result
        
        result["is_valid"] = True
        result["sanitized_data"] = email.lower().strip()
        return result
        
    except Exception as e:
        result["errors"].append(f"Email validation error: {str(e)}")
        return result


def validate_phone(phone: str) -> Dict[str, Any]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "sanitized_data": phone,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Check length (7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            result["errors"].append("Phone number must be 7-15 digits")
            return result
        
        # Check for suspicious patterns
        if digits_only.startswith("000"):
            result["warnings"].append("Phone number starts with suspicious pattern")
        
        result["is_valid"] = True
        result["sanitized_data"] = digits_only
        return result
        
    except Exception as e:
        result["errors"].append(f"Phone validation error: {str(e)}")
        return result


def validate_card_number_input(card_number: str) -> Dict[str, Any]:
    """
    Validate card number input format.
    
    Args:
        card_number: Card number to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "sanitized_data": card_number,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Remove spaces and dashes
        clean_number = re.sub(r'[\s\-]', '', card_number)
        
        # Check if contains only digits
        if not clean_number.isdigit():
            result["errors"].append("Card number must contain only digits")
            return result
        
        # Check length
        if len(clean_number) < 13 or len(clean_number) > 19:
            result["errors"].append("Card number must be 13-19 digits")
            return result
        
        # Check for test card numbers
        test_patterns = [
            r"^4\d{12}(\d{3})?$",  # Visa test numbers
            r"^5[1-5]\d{14}$",     # Mastercard test numbers
        ]
        
        for pattern in test_patterns:
            if re.match(pattern, clean_number):
                result["warnings"].append("Card number appears to be a test number")
                break
        
        result["is_valid"] = True
        result["sanitized_data"] = clean_number
        return result
        
    except Exception as e:
        result["errors"].append(f"Card number validation error: {str(e)}")
        return result


def validate_json(data: str) -> Dict[str, Any]:
    """
    Validate JSON format.
    
    Args:
        data: JSON string to validate
        
    Returns:
        dict: Validation results
    """
    result = {
        "is_valid": False,
        "sanitized_data": data,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Parse JSON
        parsed_data = json.loads(data)
        
        # Check for suspicious content in JSON
        if isinstance(parsed_data, dict):
            for key, value in parsed_data.items():
                if isinstance(value, str):
                    # Check for script tags
                    if "<script" in value.lower():
                        result["errors"].append("JSON contains script tags")
                        return result
                    
                    # Check for SQL injection patterns
                    sql_patterns = [
                        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                        r"(--|/\*|\*/)",
                    ]
                    
                    for pattern in sql_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            result["errors"].append("JSON contains suspicious SQL patterns")
                            return result
        
        result["is_valid"] = True
        result["sanitized_data"] = parsed_data
        return result
        
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON format: {str(e)}")
        return result
    except Exception as e:
        result["errors"].append(f"JSON validation error: {str(e)}")
        return result


def sanitize_input(data: Any) -> Any:
    """
    Sanitize input data to prevent injection attacks.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data


def sanitize_string(text: str) -> str:
    """
    Sanitize string input.
    
    Args:
        text: String to sanitize
        
    Returns:
        Sanitized string
    """
    if not text:
        return text
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def get_client_ip(request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token
        
    Returns:
        str: Secure random token
    """
    import secrets
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """
    Hash password using secure algorithm.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password
        hashed: Hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        dict: Password strength validation results
    """
    result = {
        "is_strong": False,
        "score": 0,
        "errors": [],
        "warnings": []
    }
    
    # Check length
    if len(password) < 8:
        result["errors"].append("Password must be at least 8 characters long")
    elif len(password) >= 12:
        result["score"] += 2
    else:
        result["score"] += 1
    
    # Check for uppercase letters
    if re.search(r'[A-Z]', password):
        result["score"] += 1
    else:
        result["warnings"].append("Password should contain uppercase letters")
    
    # Check for lowercase letters
    if re.search(r'[a-z]', password):
        result["score"] += 1
    else:
        result["warnings"].append("Password should contain lowercase letters")
    
    # Check for digits
    if re.search(r'\d', password):
        result["score"] += 1
    else:
        result["warnings"].append("Password should contain numbers")
    
    # Check for special characters
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        result["score"] += 1
    else:
        result["warnings"].append("Password should contain special characters")
    
    # Check for common patterns
    common_patterns = [
        r"123456",
        r"password",
        r"qwerty",
        r"admin",
        r"letmein",
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password, re.IGNORECASE):
            result["errors"].append("Password contains common weak patterns")
            break
    
    # Determine if password is strong
    result["is_strong"] = result["score"] >= 4 and not result["errors"]
    
    return result


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "info") -> None:
    """
    Log security events for monitoring and auditing.
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Event severity (info, warning, error, critical)
    """
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": details
    }
    
    if severity == "critical":
        logger.critical(f"Security event: {json.dumps(log_data)}")
    elif severity == "error":
        logger.error(f"Security event: {json.dumps(log_data)}")
    elif severity == "warning":
        logger.warning(f"Security event: {json.dumps(log_data)}")
    else:
        logger.info(f"Security event: {json.dumps(log_data)}")