from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    AuthContext,
    get_auth_context,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.domain.organization import OrganizationRole
from app.models.organization import Organization
from app.models.organization_membership import (
    OrganizationMembership,
)
from app.models.user import User


@dataclass(frozen=True)
class OrganizationContext:
    user: User
    organization: Organization
    role: OrganizationRole


async def get_organization_context(
    organization_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationContext:

    try:
        parsed_id = UUID(organization_id)
    except ValueError:
        organization_condition = (
            Organization.slug == organization_id
        )
    else:
        organization_condition = (
            Organization.id == parsed_id
        )
    
    stmt = (
        select(
            Organization,
            OrganizationMembership.role,
        )
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id
            == Organization.id,
        )
        .where(
            organization_condition,
            OrganizationMembership.user_id == auth.user.id,
        )
    )

    async with db.begin():
        result = await db.execute(stmt)
        row = result.one_or_none()

    if row is None:
        raise NotFoundError("Organization not found")

    organization, role = row

    return OrganizationContext(
        user=auth.user,
        organization=organization,
        role=role,
    )


def require_organization_roles(
    *allowed_roles: OrganizationRole,
):
    if not allowed_roles:
        raise ValueError("At least one role is required")

    allowed = frozenset(allowed_roles)

    async def check_roles(
        org_context: Annotated[
            OrganizationContext,
            Depends(get_organization_context),
        ],
    ) -> OrganizationContext:

        if org_context.role not in allowed:
            raise ForbiddenError(
                "Insufficient organization permissions"
            )

        return org_context

    return check_roles