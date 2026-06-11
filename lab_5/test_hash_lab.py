import hashlib
import pytest
from hash_lab import (
    sha256_hex,
    sha256_bytes,
    truncated_bits,
    expected_trials,
    find_collision,
    verify_collision,
)


def test_sha256_matches_hashlib():
    data = b"test vector"
    assert sha256_bytes(data) == hashlib.sha256(data).digest()
    assert sha256_hex(data) == hashlib.sha256(data).hexdigest()


def test_truncated_full_256():
    data = b"x"
    full = int.from_bytes(hashlib.sha256(data).digest(), "big")
    assert truncated_bits(data, 256) == full


def test_truncated_8_is_high_byte():
    data = b"abc"
    h = hashlib.sha256(data).digest()
    high_byte = h[0]
    assert truncated_bits(data, 8) == high_byte


def test_truncated_consistent():
    assert truncated_bits(b"m", 24) == truncated_bits(b"m", 24)


def test_truncated_invalid_bits():
    with pytest.raises(ValueError):
        truncated_bits(b"a", 0)
    with pytest.raises(ValueError):
        truncated_bits(b"a", 257)


def test_find_collision_small_space():
    """8 бит — ожидаемо ~19 сообщений до коллизии; должно уложиться быстро."""
    a, b, n, val = find_collision(8, max_trials=50_000)
    assert a != b
    assert verify_collision(a, b, 8)
    assert truncated_bits(a, 8) == val == truncated_bits(b, 8)
    assert n < 50_000


def test_verify_collision_false_equal_messages():
    assert verify_collision(b"x", b"x", 16) is False


def test_expected_birthday_order():
    """Для 16 бит ожидание порядка 2^8 * const ≈ сотни."""
    e16 = expected_trials(16)
    assert 200 < e16 < 400
    e20 = expected_trials(20)
    assert e20 > e16