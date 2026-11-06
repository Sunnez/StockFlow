from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.domain.organization import OrganizationRole

OrganizationName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class OrganizationCreate(BaseModel):
    name: OrganizationName

    model_config = ConfigDict(extra="forbid")


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationWithRoleRead(OrganizationRead):
    role: OrganizationRole


class OrganizationUpdate(BaseModel):
    name: OrganizationName

    model_config = ConfigDict(extra="forbid")


class OrganizationMemberRead(BaseModel):
    user_id: UUID
    email: EmailStr
    role: OrganizationRole
    joined_at: datetime


class OrganizationMemberCreate(BaseModel):
    email: EmailStr
    role: OrganizationRole

    model_config = ConfigDict(extra="forbid")