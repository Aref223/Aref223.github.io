"""
Encryption utilities for secure data handling.

This module provides encryption and decryption functions for sensitive
card data using AES-256-GCM encryption with proper key management.
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


def generate_encryption_key() -> bytes:
    """
    Generate a new encryption key.
    
    Returns:
        bytes: Generated encryption key
    """
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive encryption key from password using PBKDF2.
    
    Args:
        password: Password to derive key from
        salt: Salt for key derivation (generated if None)
        
    Returns:
        tuple: (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data using AES-256-GCM.
    
    Args:
        data: Plain text data to encrypt
        
    Returns:
        str: Base64 encoded encrypted data
        
    Raises:
        ValueError: If encryption fails
    """
    try:
        # Generate a random key and salt
        key, salt = derive_key_from_password(settings.ENCRYPTION_KEY)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data.encode()) + encryptor.finalize()
        
        # Combine salt, nonce, and ciphertext
        encrypted_data = salt + encryptor.nonce + ciphertext
        
        # Return base64 encoded result
        return base64.b64encode(encrypted_data).decode()
        
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError(f"Encryption failed: {e}")


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        
    Returns:
        str: Decrypted plain text data
        
    Raises:
        ValueError: If decryption fails
    """
    try:
        # Decode base64 data
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        
        # Extract salt, nonce, and ciphertext
        salt = encrypted_bytes[:16]
        nonce = encrypted_bytes[16:32]
        ciphertext = encrypted_bytes[32:]
        
        # Derive key from password and salt
        key, _ = derive_key_from_password(settings.ENCRYPTION_KEY, salt)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode()
        
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Decryption failed: {e}")


def encrypt_file(file_path: str, output_path: Optional[str] = None) -> str:
    """
    Encrypt a file using AES-256-GCM.
    
    Args:
        file_path: Path to file to encrypt
        output_path: Path for encrypted file (auto-generated if None)
        
    Returns:
        str: Path to encrypted file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If encryption fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if output_path is None:
        output_path = f"{file_path}.encrypted"
    
    try:
        # Read file data
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Encrypt data
        encrypted_data = encrypt_data(data.decode())
        
        # Write encrypted data
        with open(output_path, 'w') as f:
            f.write(encrypted_data)
        
        return output_path
        
    except Exception as e:
        logger.error(f"File encryption failed: {e}")
        raise ValueError(f"File encryption failed: {e}")


def decrypt_file(file_path: str, output_path: Optional[str] = None) -> str:
    """
    Decrypt a file using AES-256-GCM.
    
    Args:
        file_path: Path to encrypted file
        output_path: Path for decrypted file (auto-generated if None)
        
    Returns:
        str: Path to decrypted file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If decryption fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if output_path is None:
        output_path = file_path.replace('.encrypted', '.decrypted')
    
    try:
        # Read encrypted data
        with open(file_path, 'r') as f:
            encrypted_data = f.read()
        
        # Decrypt data
        decrypted_data = decrypt_data(encrypted_data)
        
        # Write decrypted data
        with open(output_path, 'w') as f:
            f.write(decrypted_data)
        
        return output_path
        
    except Exception as e:
        logger.error(f"File decryption failed: {e}")
        raise ValueError(f"File decryption failed: {e}")


def hash_sensitive_data(data: str) -> str:
    """
    Create a secure hash of sensitive data for comparison.
    
    Args:
        data: Data to hash
        
    Returns:
        str: SHA-256 hash of the data
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


def verify_data_integrity(original_hash: str, data: str) -> bool:
    """
    Verify data integrity by comparing hashes.
    
    Args:
        original_hash: Original hash to compare against
        data: Data to verify
        
    Returns:
        bool: True if hashes match, False otherwise
    """
    current_hash = hash_sensitive_data(data)
    return current_hash == original_hash


class SecureDataManager:
    """
    Secure data manager for handling encrypted data operations.
    
    This class provides a high-level interface for secure data handling
    with automatic encryption/decryption and integrity verification.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize secure data manager.
        
        Args:
            encryption_key: Encryption key (uses settings if None)
        """
        self.encryption_key = encryption_key or settings.ENCRYPTION_KEY
    
    def store_secure_data(self, data: str, data_id: str) -> dict:
        """
        Store data securely with integrity verification.
        
        Args:
            data: Data to store
            data_id: Unique identifier for the data
            
        Returns:
            dict: Storage metadata including hash and encrypted data
        """
        # Create hash for integrity verification
        data_hash = hash_sensitive_data(data)
        
        # Encrypt data
        encrypted_data = encrypt_data(data)
        
        return {
            "data_id": data_id,
            "encrypted_data": encrypted_data,
            "data_hash": data_hash,
            "encryption_algorithm": "AES-256-GCM",
            "created_at": str(datetime.utcnow())
        }
    
    def retrieve_secure_data(self, storage_metadata: dict) -> str:
        """
        Retrieve and verify secure data.
        
        Args:
            storage_metadata: Metadata from store_secure_data
            
        Returns:
            str: Decrypted and verified data
            
        Raises:
            ValueError: If data integrity check fails
        """
        # Decrypt data
        decrypted_data = decrypt_data(storage_metadata["encrypted_data"])
        
        # Verify integrity
        if not verify_data_integrity(storage_metadata["data_hash"], decrypted_data):
            raise ValueError("Data integrity check failed")
        
        return decrypted_data
    
    def update_secure_data(self, storage_metadata: dict, new_data: str) -> dict:
        """
        Update securely stored data.
        
        Args:
            storage_metadata: Current storage metadata
            new_data: New data to store
            
        Returns:
            dict: Updated storage metadata
        """
        # Verify current data integrity
        self.retrieve_secure_data(storage_metadata)
        
        # Store new data
        return self.store_secure_data(new_data, storage_metadata["data_id"])