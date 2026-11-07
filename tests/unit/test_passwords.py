from app.auth.passwords import (
    hash_password,
    verify_password,
)


def test_hash_password():
    password = "MySecurePassword2026!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_verify_correct_password():
    password = "MySecurePassword2026!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    password = "MySecurePassword2026!"
    hashed = hash_password(password)

    assert verify_password("WrongPassword123", hashed) is False


def test_same_password_produces_different_hashes():
    password = "MySecurePassword2026!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)