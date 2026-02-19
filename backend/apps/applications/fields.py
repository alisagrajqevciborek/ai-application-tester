"""
Encrypted field classes for storing sensitive test credentials.
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def get_encryption_key():
    """
    Generate a Fernet encryption key from Django's SECRET_KEY.
    This ensures the key is consistent across application restarts.
    """
    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise ValueError("SECRET_KEY must be set for encryption to work")
    
    # Derive a 32-byte key from SECRET_KEY using SHA256
    key = hashlib.sha256(secret_key.encode()).digest()
    # Encode to base64 for Fernet (requires 32-byte base64-encoded key)
    return base64.urlsafe_b64encode(key)


def is_encrypted(value: str) -> bool:
    """Check if a value appears to be already encrypted."""
    if not value:
        return False
    # Fernet tokens start with 'gAAAAA' and are base64url encoded
    # They're also typically longer than 50 characters
    return value.startswith('gAAAAA') and len(value) > 50


def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet."""
    if not value:
        return value
    
    # Don't encrypt if already encrypted
    if is_encrypted(value):
        return value
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encrypting value: {e}")
        raise


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a string value using Fernet."""
    if not encrypted_value:
        return encrypted_value
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception as e:
        # If decryption fails, it might be an old unencrypted value
        # Check if it looks like base64 (encrypted) vs plain text
        # Fernet tokens are always base64url encoded and have a specific format
        if encrypted_value.startswith('gAAAAA') or len(encrypted_value) > 50:
            # Looks like encrypted data but decryption failed - log error
            logger.warning(f"Failed to decrypt value (may be corrupted or from different key): {e}")
        # Return as-is to allow backward compatibility during migration
        return encrypted_value


class EncryptedCharField(models.TextField):
    """
    A CharField that automatically encrypts values on save and decrypts on read.
    Stores encrypted data in the database as text.
    """
    
    def __init__(self, *args, **kwargs):
        # Use TextField to store encrypted data (which is base64 encoded and longer)
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None:
            return value
        return decrypt_value(value)
    
    def to_python(self, value):
        """Convert value to Python string, decrypting if needed."""
        if value is None:
            return value
        if isinstance(value, str):
            # Try to decrypt - decrypt_value handles backward compatibility
            return decrypt_value(value)
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None or value == '':
            return value
        return encrypt_value(str(value))


class EncryptedURLField(EncryptedCharField):
    """
    An URLField that automatically encrypts values on save and decrypts on read.
    """
    pass

