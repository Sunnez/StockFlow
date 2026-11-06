from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_user,
    require_csrf,
)
from app.api.dependencies.organization import (
    OrganizationContext,
    get_organization_context,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationWithRoleRead,
)
from app.services.organization import service as organization_service

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_organization(
    data: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await organization_service.create_organization(
        db,
        owner_id=current_user.id,
        name=data.name,
    )


@router.get(
    "",
    response_model=list[OrganizationWithRoleRead],
)
async def list_my_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    organizations = await organization_service.list_user_organizations(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [
        OrganizationWithRoleRead(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
            role=role,
        )
        for organization, role in organizations
    ]


@router.get(
    "/{organization_id}",
    response_model=OrganizationWithRoleRead,
)
async def get_organization(
    org_context: Annotated[
        OrganizationContext,
        Depends(get_organization_context),
    ],
):
    organization = org_context.organization

    return OrganizationWithRoleRead(
        id=organization.id,
        name=organization.name,
        created_at=organization.created_at,
        role=org_context.role,
    )