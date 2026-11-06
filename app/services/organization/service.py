from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.slugs import slug_candidates
from app.domain.organization import OrganizationRole
from app.models.organization import UQ_ORGANIZATIONS_SLUG, Organization
from app.models.organization_membership import OrganizationMembership


async def create_organization(
    db: AsyncSession,
    *,
    owner_id: UUID,
    name: str,
) -> Organization:

    organization = None

    async with db.begin():
        for slug in slug_candidates(name):
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