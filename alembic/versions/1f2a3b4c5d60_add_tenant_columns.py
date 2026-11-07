"""Add required tenant columns to empty business tables.

Revision ID: 1f2a3b4c5d60
Revises: feac2845934c

This migration is intentionally for a database with EMPTY business tables.
There is no legacy backfill or implicit ownership assignment.
"""

import sqlalchemy as sa
from alembic import op

revision = "1f2a3b4c5d60"
down_revision = "feac2845934c"
branch_labels = None
depends_on = None

BUSINESS_TABLES = (
    "products",
    "warehouses",
    "orders",
    "inventory",
    "order_items",
    "order_allocations",
)


def upgrade() -> None:
    # NOT NULL + no DEFAULT: PostgreSQL rejects this for nonempty tables.
    for table in BUSINESS_TABLES:
        op.add_column(
            table,
            sa.Column("organization_id", sa.Uuid(), nullable=False),
        )

    op.add_column(
        "order_allocations",
        sa.Column("product_id", sa.Uuid(), nullable=False),
    )

    for table in ("products", "warehouses", "orders"):
        op.create_foreign_key(
            f"fk_{table}_organization",
            table,
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    raise RuntimeError(
        "Automatic downgrade would remove tenant ownership columns. "
        "Use a separately reviewed reverse migration if necessary."
    )
