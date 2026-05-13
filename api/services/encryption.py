"""Fernet-based column-level encryption for credential values."""

from cryptography.fernet import Fernet, InvalidToken
from api.config import get_settings


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().vault_encryption_key
        if not key:
            raise RuntimeError("VAULT_ENCRYPTION_KEY is not set — cannot encrypt/decrypt credentials")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def reset_fernet():
    """Reset cached Fernet instance (useful for tests)."""
    global _fernet
    _fernet = None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a credential value. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a credential value."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt credential — key mismatch or corrupted data")
