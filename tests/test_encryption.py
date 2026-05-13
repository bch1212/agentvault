"""Tests for column-level encryption service."""

import pytest
from api.services.encryption import encrypt_value, decrypt_value, reset_fernet


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value decrypts back to original."""
        reset_fernet()
        secret = "sk_live_abc123xyz"
        encrypted = encrypt_value(secret)

        assert encrypted != secret  # must not be plaintext
        assert decrypt_value(encrypted) == secret

    def test_different_ciphertexts_per_call(self):
        """Fernet produces unique ciphertexts (nonce-based)."""
        reset_fernet()
        secret = "my_api_key_value"
        a = encrypt_value(secret)
        b = encrypt_value(secret)
        assert a != b  # same plaintext → different ciphertext

    def test_decrypt_bad_data_raises(self):
        """Decrypting garbage raises ValueError."""
        reset_fernet()
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_value("not_valid_fernet_token")

    def test_empty_string_roundtrip(self):
        """Can encrypt and decrypt empty string."""
        reset_fernet()
        encrypted = encrypt_value("")
        assert decrypt_value(encrypted) == ""

    def test_long_value_roundtrip(self):
        """Can handle long values (e.g., JWT tokens)."""
        reset_fernet()
        long_val = "x" * 10000
        encrypted = encrypt_value(long_val)
        assert decrypt_value(encrypted) == long_val
