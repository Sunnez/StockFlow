from psycopg.errors import UniqueViolation
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.passwords import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
)
from app.db.errors import get_constraint_name
from app.models.user import User
from app.services.auth.exceptions import (
    InvalidCredentialsError,
    UserEmailAlreadyExistsError,
)

UQ_USERS_EMAIL_LOWER = "uq_users_email_lower"


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:

    normalized_email = email.strip().lower()

    password_hash = await run_in_threadpool(
        hash_password,
        password,
    )

    user = User(
        email=normalized_email,
        password_hash=password_hash,
    )

    try:
        async with db.begin():
            db.add(user)
            await db.flush()

    except IntegrityError as exc:
        if (
            isinstance(exc.orig, UniqueViolation)
            and get_constraint_name(exc) == UQ_USERS_EMAIL_LOWER
        ):
            raise UserEmailAlreadyExistsError() from exc

        raise

    return user


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()

    stmt = select(User).where(
        func.lower(User.email) == normalized_email
    )

    async with db.begin():
        user = await db.scalar(stmt)

    stored_hash = (
        user.password_hash
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    is_valid_password = await run_in_threadpool(
        verify_password,
        password,
        stored_hash,
    )

    if (
        user is None
        or not user.is_active
        or not is_valid_password
    ):
        raise InvalidCredentialsError()

    return user