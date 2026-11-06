import hashlib
import secrets
from uuid import UUID, uuid4


def hash_refresh_secret(secret: str) -> str:
    return hashlib.sha256(
        secret.encode("utf-8")
    ).hexdigest()


def generate_refresh_token() -> tuple[UUID, str, str]:
    token_id = uuid4()
    secret = secrets.token_urlsafe(32)

    raw_token = f"{token_id}.{secret}"
    token_hash = hash_refresh_secret(secret)

    return token_id, raw_token, token_hash


def parse_refresh_token(raw_token: str) -> tuple[UUID, str]:
    if len(raw_token) > 256:
        raise ValueError("Invalid refresh token")

    token_id_str, separator, secret = raw_token.partition(".")

    if not separator or not secret or "." in secret:
        raise ValueError("Invalid refresh token")

    token_id = UUID(token_id_str)

    return token_id, secret