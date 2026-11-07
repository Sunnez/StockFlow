"""Transaction-local authorization. Call before taking business resource locks."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.organization import OrganizationRole
from app.models.organization_membership import OrganizationMembership

BUSINESS_WRITE_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MANAGER,
    }
)
ORGANIZATION_ADMIN_ROLES = frozenset({OrganizationRole.OWNER, OrganizationRole.ADMIN})


async def lock_actor_membership(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    allowed_roles: Collection[OrganizationRole] = BUSINESS_WRITE_ROLES,
) -> OrganizationMembership:
    # FOR SHARE allows concurrent operations but blocks membership deletion/role changes
    # until the enclosing service transaction commits. Do not open a transaction here.
    membership = await db.scalar(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == actor_id,
        )
        .execution_options(populate_existing=True)
        .with_for_update(read=True)
    )
    if membership is None:
        raise NotFoundError("Organization not found")
    if membership.role not in allowed_roles:
        raise ForbiddenError("Insufficient organization permissions")
    return membership
