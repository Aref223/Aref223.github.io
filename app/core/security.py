"""
Core security module for the Visa and Debit Card Scraper application.

This module provides the SecurityManager class and other core security
functionality for the application.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)

class SecurityManager:
    """Security manager for handling application-wide security operations."""
    
    def __init__(self):
        self.security_events = []
        self.blocked_ips = set()
        self.suspicious_activities = []
        self.rate_limit_violations = []
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], severity: str = "info") -> None:
        """Log a security event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details
        }
        
        self.security_events.append(event)
        
        if severity == "critical":
            logger.critical(f"Security event: {event}")
        elif severity == "error":
            logger.error(f"Security event: {event}")
        elif severity == "warning":
            logger.warning(f"Security event: {event}")
        else:
            logger.info(f"Security event: {event}")
    
    def check_ip_suspicious(self, ip_address: str) -> bool:
        """Check if an IP address is suspicious based on previous activities."""
        # Count recent security events for this IP
        recent_events = [
            event for event in self.security_events
            if event["details"].get("ip_address") == ip_address
            and datetime.fromisoformat(event["timestamp"]) > datetime.utcnow() - timedelta(hours=1)
        ]
        
        # Check for multiple failed login attempts
        failed_logins = [
            event for event in recent_events
            if event["event_type"] == "login_failed"
        ]
        
        # Check for rate limit violations
        rate_violations = [
            event for event in recent_events
            if event["event_type"] == "rate_limit_exceeded"
        ]
        
        # Consider suspicious if more than 5 failed logins or 3 rate violations in the last hour
        return len(failed_logins) > 5 or len(rate_violations) > 3
    
    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block an IP address."""
        self.blocked_ips.add(ip_address)
        self.log_security_event("ip_blocked", {
            "ip_address": ip_address,
            "reason": reason
        }, "warning")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is blocked."""
        return ip_address in self.blocked_ips
    
    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address."""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            self.log_security_event("ip_unblocked", {
                "ip_address": ip_address
            }, "info")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_data_integrity(self, original_hash: str, data: str) -> bool:
        """Verify data integrity by comparing hashes."""
        current_hash = self.hash_sensitive_data(data)
        return current_hash == original_hash
    
    def sanitize_input(self, data: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not data:
            return data
        
        # Remove null bytes
        data = data.replace('\x00', '')
        
        # Remove control characters
        data = ''.join(char for char in data if ord(char) >= 32 or char in '\n\r\t')
        
        # Normalize whitespace
        data = ' '.join(data.split())
        
        return data.strip()
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength."""
        result = {
            "is_strong": False,
            "score": 0,
            "errors": [],
            "warnings": []
        }
        
        if len(password) < 8:
            result["errors"].append("Password must be at least 8 characters long")
        else:
            result["score"] += 2 if len(password) >= 12 else 1
        
        if any(c.isupper() for c in password):
            result["score"] += 1
        else:
            result["warnings"].append("Password should contain uppercase letters")
        
        if any(c.islower() for c in password):
            result["score"] += 1
        else:
            result["warnings"].append("Password should contain lowercase letters")
        
        if any(c.isdigit() for c in password):
            result["score"] += 1
        else:
            result["warnings"].append("Password should contain numbers")
        
        if any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
            result["score"] += 1
        else:
            result["warnings"].append("Password should contain special characters")
        
        # Check for common weak patterns
        common_patterns = ["123456", "password", "qwerty", "admin", "letmein"]
        for pattern in common_patterns:
            if pattern.lower() in password.lower():
                result["errors"].append("Password contains common weak patterns")
                break
        
        result["is_strong"] = result["score"] >= 4 and not result["errors"]
        return result
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate a security report."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event["timestamp"]) > last_24h
        ]
        
        critical_events = [event for event in recent_events if event["severity"] == "critical"]
        error_events = [event for event in recent_events if event["severity"] == "error"]
        warning_events = [event for event in recent_events if event["severity"] == "warning"]
        
        return {
            "total_events_24h": len(recent_events),
            "critical_events": len(critical_events),
            "error_events": len(error_events),
            "warning_events": len(warning_events),
            "blocked_ips_count": len(self.blocked_ips),
            "suspicious_activities_count": len(self.suspicious_activities),
            "rate_limit_violations_count": len(self.rate_limit_violations),
            "recent_events": recent_events[-10:],  # Last 10 events
            "blocked_ips": list(self.blocked_ips)
        }
    
    def cleanup_old_events(self, days: int = 30) -> None:
        """Clean up old security events."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        self.security_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event["timestamp"]) > cutoff_date
        ]
        
        logger.info(f"Cleaned up security events older than {days} days")
    
    def reset_security_state(self) -> None:
        """Reset security state (for testing purposes)."""
        self.security_events.clear()
        self.blocked_ips.clear()
        self.suspicious_activities.clear()
        self.rate_limit_violations.clear()
        logger.info("Security state reset")