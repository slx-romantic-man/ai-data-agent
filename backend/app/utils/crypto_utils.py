"""
Crypto utilities for encrypting/decrypting sensitive API auth configurations.
Uses Fernet symmetric encryption from the cryptography library.
"""
import json
import os
import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_encryption_key() -> bytes:
    """
    Get or derive the encryption key from environment variable.

    The key can be provided in two ways:
    1. API_AUTH_ENCRYPTION_KEY - A base64-encoded Fernet key (recommended)
    2. SECRET_KEY - A passphrase that will be derived into a key (fallback)

    Returns:
        bytes: A valid Fernet key
    """
    # Try to get the dedicated encryption key first
    key_str = os.environ.get("API_AUTH_ENCRYPTION_KEY")

    if key_str:
        try:
            # If it's a valid base64 Fernet key, use it directly
            return base64.urlsafe_b64decode(key_str.encode())
        except Exception:
            # If it's not a valid Fernet key, derive one from it
            pass

    # Fallback: derive key from SECRET_KEY
    secret = os.environ.get("SECRET_KEY", "default-secret-key-change-in-production")
    salt = b"ai_data_agent_auth_encryption_salt"  # Fixed salt for key derivation

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


# Global Fernet instance (lazy initialization)
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet instance."""
    global _fernet
    if _fernet is None:
        key = _get_encryption_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_auth_config(data: dict) -> str:
    """
    Encrypt auth configuration data.

    Args:
        data: Dictionary containing auth configuration
              Example: {"type": "api_key", "header": "X-API-Key", "value": "sk-xxx"}

    Returns:
        str: Encrypted string (base64 encoded)

    Example:
        >>> auth = {"type": "bearer", "token": "abc123"}
        >>> encrypted = encrypt_auth_config(auth)
        >>> # Store encrypted in database
    """
    if not data:
        return ""

    try:
        fernet = _get_fernet()
        json_data = json.dumps(data, ensure_ascii=False)
        encrypted = fernet.encrypt(json_data.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt auth config: {e}")
        raise ValueError(f"Encryption failed: {e}")


def decrypt_auth_config(encrypted: str) -> dict:
    """
    Decrypt auth configuration data.

    Args:
        encrypted: Encrypted string from database

    Returns:
        dict: Original auth configuration dictionary

    Example:
        >>> encrypted = "gAAAAABl..."  # from database
        >>> auth = decrypt_auth_config(encrypted)
        >>> # auth = {"type": "bearer", "token": "abc123"}
    """
    if not encrypted:
        return {}

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Failed to decrypt auth config: {e}")
        raise ValueError(f"Decryption failed: {e}")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet-compatible encryption key.

    Use this to generate a key for API_AUTH_ENCRYPTION_KEY environment variable.

    Returns:
        str: Base64-encoded Fernet key

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"Set API_AUTH_ENCRYPTION_KEY={key}")
    """
    key = Fernet.generate_key()
    return key.decode()


if __name__ == "__main__":
    # Utility to generate a new key
    print("Generated encryption key:")
    print(f"API_AUTH_ENCRYPTION_KEY={generate_encryption_key()}")
    print("\nAdd this to your .env file for production use.")