from uuid import uuid4

import jwt
import pytest

from app.auth.jwt import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    decode_access_token,
)
from app.core.config import settings


def test_access_token_roundtrip():
    user_id = uuid4()

    token = create_access_token(user_id)

    assert isinstance(token, str)
    assert decode_access_token(token) == user_id


def test_access_token_contains_required_claims():
    user_id = uuid4()
    token = create_access_token(user_id)

    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]
    assert payload["jti"]


def test_access_token_rejects_wrong_signature():
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "type": "access",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": 1793541600,
            "exp": 4102444800,
            "jti": str(uuid4()),
        },
        "a-completely-different-secret-key",
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)