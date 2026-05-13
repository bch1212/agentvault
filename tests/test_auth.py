"""Tests for auth services — API key generation, hashing, agent lookup."""

import pytest
from api.services.auth import generate_api_key, hash_api_key, get_key_prefix


class TestApiKeyGeneration:
    def test_key_has_prefix(self):
        key = generate_api_key()
        assert key.startswith("avk_")

    def test_keys_are_unique(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_key_length(self):
        key = generate_api_key()
        assert len(key) > 40  # avk_ + 48 bytes base64

    def test_hash_is_deterministic(self):
        key = generate_api_key()
        assert hash_api_key(key) == hash_api_key(key)

    def test_hash_differs_for_different_keys(self):
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)

    def test_prefix_extraction(self):
        key = "avk_abcdefghijk_rest"
        assert get_key_prefix(key) == "avk_abcdefgh"
