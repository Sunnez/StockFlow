from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


UQ_INVENTORY_PRODUCT_WAREHOUSE = "uq_inventory_product_warehouse"

CK_INVENTORY_QUANTITY_NON_NEGATIVE = "ck_inventory_quantity_non_negative"


FK_INVENTORY_PRODUCT = "fk_inventory_product"
FK_INVENTORY_WAREHOUSE = "fk_inventory_warehouse"


class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name=UQ_INVENTORY_PRODUCT_WAREHOUSE,
        ),
        CheckConstraint(
            "quantity >= 0",
            name=CK_INVENTORY_QUANTITY_NON_NEGATIVE,
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            name=FK_INVENTORY_PRODUCT,
        ),
        nullable=False,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey(
            "warehouses.id",
            name=FK_INVENTORY_WAREHOUSE,
        ),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )