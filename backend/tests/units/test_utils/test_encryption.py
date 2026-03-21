"""Unit tests for app.utils.encryption module."""

import pytest

import app.utils.encryption as enc_module


@pytest.fixture(autouse=True)
def reset_fernet(monkeypatch):
    """Reset the module-level _fernet singleton before each test so that
    different encryption keys don't bleed between tests."""
    monkeypatch.setattr(enc_module, "_fernet", None)
    yield
    monkeypatch.setattr(enc_module, "_fernet", None)


# ---------------------------------------------------------------------------
# _get_encryption_key
# ---------------------------------------------------------------------------


def test_get_encryption_key_uses_encryption_key_env(monkeypatch):
    """When ENCRYPTION_KEY is set it is used directly."""
    from cryptography.fernet import Fernet

    raw_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", raw_key)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    key = enc_module._get_encryption_key()
    assert key == raw_key.encode()


def test_get_encryption_key_derives_from_jwt_secret(monkeypatch):
    """When ENCRYPTION_KEY is absent, key is derived from JWT_SECRET."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "my-jwt-secret")

    key = enc_module._get_encryption_key()
    # Key must be 44 bytes (URL-safe base64-encoded 32-byte digest)
    assert isinstance(key, bytes)
    assert len(key) == 44


def test_get_encryption_key_derived_key_is_deterministic(monkeypatch):
    """Same JWT_SECRET always produces the same derived key."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "stable-secret")

    key1 = enc_module._get_encryption_key()
    key2 = enc_module._get_encryption_key()
    assert key1 == key2


def test_get_encryption_key_raises_when_both_missing(monkeypatch):
    """RuntimeError raised when neither ENCRYPTION_KEY nor JWT_SECRET is set."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY or JWT_SECRET"):
        enc_module._get_encryption_key()


def test_get_encryption_key_encryption_key_takes_priority(monkeypatch):
    """ENCRYPTION_KEY is preferred over JWT_SECRET."""
    from cryptography.fernet import Fernet

    raw_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", raw_key)
    monkeypatch.setenv("JWT_SECRET", "should-be-ignored")

    key = enc_module._get_encryption_key()
    assert key == raw_key.encode()


# ---------------------------------------------------------------------------
# encrypt_api_key / decrypt_api_key
# ---------------------------------------------------------------------------


def test_encrypt_returns_string_different_from_input(monkeypatch):
    """encrypt_api_key must return a string that differs from the plain key."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = "my-secret-api-key-1234"
    encrypted = enc_module.encrypt_api_key(plain)

    assert isinstance(encrypted, str)
    assert encrypted != plain


def test_encrypt_decrypt_roundtrip(monkeypatch):
    """decrypt(encrypt(x)) == x for an arbitrary key."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = "super-secret-key-ABCDE12345"
    assert enc_module.decrypt_api_key(enc_module.encrypt_api_key(plain)) == plain


def test_encrypt_decrypt_roundtrip_empty_string(monkeypatch):
    """Empty string round-trips correctly (edge case)."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = ""
    assert enc_module.decrypt_api_key(enc_module.encrypt_api_key(plain)) == plain


def test_encrypt_produces_different_ciphertexts_each_call(monkeypatch):
    """Fernet uses a random nonce — two encryptions of the same value differ."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = "same-key"
    enc1 = enc_module.encrypt_api_key(plain)
    enc2 = enc_module.encrypt_api_key(plain)
    # Both decrypt to the same value but the ciphertexts are different
    assert enc1 != enc2
    assert enc_module.decrypt_api_key(enc1) == plain
    assert enc_module.decrypt_api_key(enc2) == plain


def test_decrypt_wrong_key_raises(monkeypatch):
    """Decrypting with a different key raises an error."""
    from cryptography.fernet import Fernet, InvalidToken

    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()

    monkeypatch.setenv("ENCRYPTION_KEY", key1)
    encrypted = enc_module.encrypt_api_key("secret")

    # Reset singleton so a new Fernet with key2 is created
    monkeypatch.setattr(enc_module, "_fernet", None)
    monkeypatch.setenv("ENCRYPTION_KEY", key2)

    with pytest.raises(InvalidToken):
        enc_module.decrypt_api_key(encrypted)


def test_encrypt_long_key(monkeypatch):
    """Very long API keys survive the round-trip."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = "x" * 500
    assert enc_module.decrypt_api_key(enc_module.encrypt_api_key(plain)) == plain


def test_encrypt_unicode_key(monkeypatch):
    """Keys containing unicode characters survive the round-trip."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

    plain = "ключ-api-кирилица-🔑"
    assert enc_module.decrypt_api_key(enc_module.encrypt_api_key(plain)) == plain


# ---------------------------------------------------------------------------
# mask_api_key
# ---------------------------------------------------------------------------


def test_mask_api_key_normal_key():
    """Standard key: last 4 chars shown, rest masked."""
    result = enc_module.mask_api_key("abcdef1234")
    assert result == "******1234"


def test_mask_api_key_exactly_four_chars():
    """Key with exactly 4 characters → all masked."""
    result = enc_module.mask_api_key("1234")
    assert result == "****"


def test_mask_api_key_two_chars():
    """Key shorter than 4 chars → all masked."""
    result = enc_module.mask_api_key("ab")
    assert result == "**"


def test_mask_api_key_one_char():
    """Single-character key → one asterisk."""
    result = enc_module.mask_api_key("x")
    assert result == "*"


def test_mask_api_key_five_chars():
    """Five chars: first one masked, last four shown."""
    result = enc_module.mask_api_key("12345")
    assert result == "*2345"


def test_mask_api_key_long_key():
    """Long key: only last 4 chars are visible."""
    key = "a" * 100 + "TAIL"
    result = enc_module.mask_api_key(key)
    assert result.endswith("TAIL")
    assert result.count("*") == 100
    assert len(result) == 104


def test_mask_api_key_preserves_total_length():
    """Output length always equals input length."""
    for length in range(1, 20):
        key = "k" * length
        result = enc_module.mask_api_key(key)
        assert len(result) == length, f"Length mismatch for key of length {length}"
