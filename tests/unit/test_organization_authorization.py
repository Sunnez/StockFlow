from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.api.dependencies.auth import AuthContext
from app.api.dependencies.organization import (
    get_organization_context,
    require_organization_roles,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.organization import OrganizationRole
from app.models.organization import Organization
from app.models.user import User
from app.services.organization.authorization import lock_actor_membership


def mock_db():
    db = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)
    db.begin = MagicMock(return_value=transaction)
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("use_slug", [True, False])
async def test_uuid_slug_resolver_is_member_filtered_and_returns_internal_uuid(
    use_slug,
):
    db = mock_db()
    org = Organization(id=uuid4(), slug="acme")
    user = User(id=uuid4(), is_active=True)
    result = MagicMock()
    result.one_or_none.return_value = (org, OrganizationRole.VIEWER)
    db.execute.return_value = result
    context = await get_organization_context(
        org.slug if use_slug else str(org.id), AuthContext(user, uuid4()), db
    )
    assert context.organization.id == org.id
    assert context.role == OrganizationRole.VIEWER
    stmt = db.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert user.id in stmt.params.values()
    assert (org.slug if use_slug else org.id) in stmt.params.values()
    assert "organization_memberships.user_id" in str(stmt)
    assert ("organizations.slug =" if use_slug else "organizations.id =") in str(stmt)


@pytest.mark.asyncio
async def test_nonmember_and_nonexistent_organization_have_same_error():
    db = mock_db()
    result = MagicMock()
    result.one_or_none.return_value = None
    db.execute.return_value = result
    with pytest.raises(NotFoundError, match="Organization not found"):
        await get_organization_context(
            "acme", AuthContext(User(id=uuid4()), uuid4()), db
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", list(OrganizationRole))
async def test_business_write_role_dependency(role):
    context = SimpleNamespace(role=role)
    check = require_organization_roles(
        OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MANAGER
    )
    if role == OrganizationRole.VIEWER:
        with pytest.raises(ForbiddenError):
            await check(context)
    else:
        assert await check(context) is context


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [None, *OrganizationRole])
async def test_service_reloads_and_locks_membership_before_business_write(role):
    db = mock_db()
    organization_id, actor_id = uuid4(), uuid4()
    membership = None if role is None else SimpleNamespace(role=role)
    db.scalar.return_value = membership
    if role is None:
        with pytest.raises(NotFoundError):
            await lock_actor_membership(
                db, organization_id=organization_id, actor_id=actor_id
            )
    elif role == OrganizationRole.VIEWER:
        with pytest.raises(ForbiddenError):
            await lock_actor_membership(
                db, organization_id=organization_id, actor_id=actor_id
            )
    else:
        assert (
            await lock_actor_membership(
                db, organization_id=organization_id, actor_id=actor_id
            )
            is membership
        )
    stmt = db.scalar.call_args.args[0]
    assert stmt.get_execution_options()["populate_existing"] is True
    compiled = stmt.compile(dialect=postgresql.dialect())
    assert "FOR SHARE" in str(compiled)
    assert {organization_id, actor_id} <= set(compiled.params.values())
    db.begin.assert_not_called()  # caller owns transaction/rollback
