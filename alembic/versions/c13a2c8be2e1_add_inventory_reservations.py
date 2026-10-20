"""add inventory reservations

Revision ID: c13a2c8be2e1
Revises: a6a1e61f8865
Create Date: 2026-10-19 21:12:53.331645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c13a2c8be2e1"
down_revision: Union[str, Sequence[str], None] = "a6a1e61f8865"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory",
        sa.Column(
            "reserved_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_inventory_reserved_quantity_non_negative",
        "inventory",
        "reserved_quantity >= 0",
    )

    op.create_check_constraint(
        "ck_inventory_reserved_not_greater_than_quantity",
        "inventory",
        "reserved_quantity <= quantity",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_reserved_not_greater_than_quantity",
        "inventory",
        type_="check",
    )

    op.drop_constraint(
        "ck_inventory_reserved_quantity_non_negative",
        "inventory",
        type_="check",
    )

    op.drop_column(
        "inventory",
        "reserved_quantity",
    )