from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ApplicationValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.slugs import slug_candidates
from app.domain.organization import ROLE_LEVEL, OrganizationRole
from app.models.organization import UQ_ORGANIZATIONS_SLUG, Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.schemas.organization import OrganizationMemberRead


async def create_organization(
    db: AsyncSession,
    *,
    owner_id: UUID,
    name: str,
) -> Organization:

    organization = None

    async with db.begin():
        for slug in slug_candidates(name, fallback="organization"):
            stmt = (
                insert(Organization)
                .values(
                    id=uuid4(),
                    name=name,
                    slug=slug,
                )
                .on_conflict_do_nothing(
                    constraint=UQ_ORGANIZATIONS_SLUG,
                )
                .returning(Organization)
            )

            organization = await db.scalar(stmt)

            if organization is not None:
                break

        if organization is None:
            raise ConflictError(
                "Could not generate a unique organization slug"
            )

        membership = OrganizationMembership(
            user_id=owner_id,
            organization_id=organization.id,
            role=OrganizationRole.OWNER,
        )

        db.add(membership)
        await db.flush()

    return organization


async def list_user_organizations(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[Organization, OrganizationRole]]:

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
            OrganizationMembership.user_id == user_id,
        )
        .order_by(
            Organization.created_at.desc(),
            Organization.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    async with db.begin():
        result = await db.execute(stmt)
        rows = result.all()

    return [
        (organization, role)
        for organization, role in rows
    ]


async def update_organization_name(
    db: AsyncSession,
    *,
    organization_id: UUID,
    name: str,
) -> Organization:

    async with db.begin():
        stmt = (
            select(Organization)
            .where(Organization.id == organization_id)
            .with_for_update()
        )

        organization = await db.scalar(stmt)

        if organization is None:
            raise NotFoundError("Organization not found")

        organization.name = name

        await db.flush()

    return organization


async def list_organization_members(
    db: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[OrganizationMemberRead]:

    stmt = (
        select(
            User.id,
            User.email,
            OrganizationMembership.role,
            OrganizationMembership.created_at,
        )
        .join(
            OrganizationMembership,
            OrganizationMembership.user_id == User.id,
        )
        .where(
            OrganizationMembership.organization_id == organization_id,
        )
        .order_by(
            OrganizationMembership.created_at,
            User.id,
        )
        .limit(limit)
        .offset(offset)
    )

    async with db.begin():
        result = await db.execute(stmt)
        rows = result.all()

    return [
        OrganizationMemberRead(
            user_id=user_id,
            email=email,
            role=role,
            joined_at=created_at,
        )
        for user_id, email, role, created_at in rows
    ]


async def add_organization_member(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    email: str,
    role: OrganizationRole,
) -> OrganizationMemberRead:

    if role == OrganizationRole.OWNER:
        raise ApplicationValidationError(
            "Owner role cannot be assigned directly"
        )

    async with db.begin():
        actor_membership = await db.scalar(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == actor_id,
            )
            .with_for_update()
        )

        if actor_membership is None:
            raise NotFoundError("Organization not found")

        if actor_membership.role == OrganizationRole.OWNER:
            allowed_roles = {
                OrganizationRole.ADMIN,
                OrganizationRole.MANAGER,
                OrganizationRole.VIEWER,
            }

        elif actor_membership.role == OrganizationRole.ADMIN:
            allowed_roles = {
                OrganizationRole.MANAGER,
                OrganizationRole.VIEWER,
            }

        else:
            raise ForbiddenError(
                "Insufficient organization permissions"
            )

        if role not in allowed_roles:
            raise ForbiddenError(
                "Cannot assign the requested role"
            )

        user = await db.scalar(
            select(User).where(
                func.lower(User.email) == email.strip().lower(),
                User.is_active.is_(True),
            )
        )

        if user is None:
            raise NotFoundError("User not found")

        stmt = (
            insert(OrganizationMembership)
            .values(
                user_id=user.id,
                organization_id=organization_id,
                role=role,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    OrganizationMembership.user_id,
                    OrganizationMembership.organization_id,
                ],
            )
            .returning(OrganizationMembership.created_at)
        )

        joined_at = await db.scalar(stmt)

        if joined_at is None:
            raise ConflictError(
                "User is already a member of this organization"
            )

    return OrganizationMemberRead(
        user_id=user.id,
        email=user.email,
        role=role,
        joined_at=joined_at,
    )


async def remove_organization_member(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    target_user_id: UUID,
) -> None:

    if actor_id == target_user_id:
        raise ForbiddenError(
            "You cannot remove yourself from the organization"
        )

    async with db.begin():
        stmt = (
            select(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id.in_(
                    [actor_id, target_user_id]
                ),
            )
            .order_by(OrganizationMembership.user_id)
            .with_for_update()
        )

        result = await db.execute(stmt)

        memberships = {
            membership.user_id: membership
            for membership in result.scalars().all()
        }

        actor = memberships.get(actor_id)
        target = memberships.get(target_user_id)

        if actor is None:
            raise NotFoundError("Organization not found")

        if target is None:
            raise NotFoundError("Organization member not found")

        if ROLE_LEVEL[actor.role] <= ROLE_LEVEL[target.role]:
            raise ForbiddenError(
                "Cannot remove a member with equal or higher role"
            )

        await db.delete(target)
        await db.flush()