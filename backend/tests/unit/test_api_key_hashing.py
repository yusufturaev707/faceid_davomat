"""API key hashing unit testlari — HMAC-SHA256 + legacy SHA-256 verify."""
from app.crud.api_key import _hash_legacy, _hash_v2, _verify, HASH_VERSION


def test_v2_hash_includes_version_prefix():
    h = _hash_v2("sk-test123")
    assert h.startswith(f"{HASH_VERSION}:")


def test_v2_hash_deterministic():
    assert _hash_v2("sk-abc") == _hash_v2("sk-abc")


def test_v2_verify_success():
    raw = "sk-unique-raw-key"
    assert _verify(raw, _hash_v2(raw))


def test_v2_verify_fails_on_wrong_key():
    assert not _verify("sk-wrong", _hash_v2("sk-right"))


def test_legacy_sha256_still_verifiable():
    """Eski API kalitlarga backward compatibility."""
    raw = "sk-legacy-key"
    assert _verify(raw, _hash_legacy(raw))


def test_v2_and_legacy_produce_different_hashes():
    raw = "sk-same"
    assert _hash_v2(raw) != _hash_legacy(raw)
