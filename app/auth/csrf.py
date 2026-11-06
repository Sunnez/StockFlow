import hashlib
import hmac
import re
import secrets
from uuid import UUID

from app.core.config import settings


def _csrf_signature(
    session_id: UUID,
    nonce: str,
) -> str:
    message = f"{session_id}:{nonce}".encode("utf-8")

    return hmac.new(
        settings.csrf_secret_key.get_secret_value().encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def generate_csrf_token(session_id: UUID) -> str:
    nonce = secrets.token_urlsafe(32)
    signature = _csrf_signature(session_id, nonce)

    return f"{nonce}.{signature}"


def verify_csrf_token(
    session_id: UUID,
    cookie_token: str | None,
    header_token: str | None,
) -> bool:
    if not cookie_token or not header_token:
        return False

    if len(cookie_token) > 256 or len(header_token) > 256:
        return False

    if not hmac.compare_digest(cookie_token, header_token):
        return False

    nonce, separator, signature = header_token.partition(".")

    if not separator:
        return False

    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", nonce):
        return False

    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        return False

    expected_signature = _csrf_signature(session_id, nonce)

    return hmac.compare_digest(
        signature,
        expected_signature,
    )