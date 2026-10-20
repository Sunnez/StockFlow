from uuid import UUID, uuid4

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


UQ_WAREHOUSES_NAME = "uq_warehouses_name"


class Warehouse(Base):
    __tablename__ = "warehouses"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name=UQ_WAREHOUSES_NAME,
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

    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
