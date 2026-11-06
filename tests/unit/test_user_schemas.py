import pytest

from pydantic import ValidationError

from app.schemas.user import UserCreate


def test_valid_user_create():
    user = UserCreate(
        email="alex@example.com",
        password="SecurePassword123!",
    )

    assert str(user.email) == "alex@example.com"


def test_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            password="SecurePassword123!",
        )


def test_short_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="alex@example.com",
            password="12345",
        )


def test_forbidden_extra_fields():
    with pytest.raises(ValidationError):
        UserCreate.model_validate({
            "email": "alex@example.com",
            "password": "SecurePassword123!",
            "is_superuser": True,
        })