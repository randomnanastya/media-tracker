"""Fernet encryption utilities for API keys."""

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from app.config import logger


def _get_encryption_key() -> bytes:
    """Get Fernet key from ENCRYPTION_KEY env or derive from JWT_SECRET."""
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        return key.encode()

    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("Either ENCRYPTION_KEY or JWT_SECRET must be set")

    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        logger.warning(
            "ENCRYPTION_KEY not set in production, deriving from JWT_SECRET. "
            "Set ENCRYPTION_KEY for better security."
        )

    derived = hashlib.sha256(jwt_secret.encode()).digest()
    return base64.urlsafe_b64encode(derived)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_encryption_key())
    return _fernet


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt API key, return base64-encoded ciphertext."""
    return str(_get_fernet().encrypt(plain_key.encode()).decode())


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key from base64-encoded ciphertext."""
    return str(_get_fernet().decrypt(encrypted_key.encode()).decode())


def mask_api_key(plain_key: str) -> str:
    """Mask API key for display: show only last 4 chars."""
    if len(plain_key) <= 4:
        return "*" * len(plain_key)
    return "*" * (len(plain_key) - 4) + plain_key[-4:]
