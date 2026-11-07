from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "stockflow"
JWT_AUDIENCE = "stockflow-api"


def create_access_token(
    user_id: UUID,
    session_id: UUID,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.jwt_access_expire_minutes,
        ),
        "jti": str(uuid4()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[UUID, UUID]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={
            "require": [
                "sub",
                "sid",
                "type",
                "iss",
                "aud",
                "iat",
                "exp",
                "jti",
            ],
        },
    )

    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    try:
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise jwt.InvalidTokenError(
            "Invalid token identifiers"
        ) from exc

    return user_id, session_id