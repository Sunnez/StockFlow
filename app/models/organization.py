from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization_membership import OrganizationMembership


UQ_ORGANIZATIONS_SLUG = "uq_organizations_slug"

class Organization(Base):
    __tablename__ = "organizations"

    __table_args__ = (
        UniqueConstraint(
            "slug",
            name=UQ_ORGANIZATIONS_SLUG,
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    memberships: Mapped[list[OrganizationMembership]] = (
        relationship(
            back_populates="organization",
        )
    )