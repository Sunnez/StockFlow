"""Enforce tenant-specific uniqueness and relational integrity.

Revision ID: 1f2a3b4c5d61
Revises: 1f2a3b4c5d60

No data mapping or legacy-row handling: business tables must be empty
before revision 1f2a3b4c5d60 is applied.
"""

from alembic import op

revision = "1f2a3b4c5d61"
down_revision = "1f2a3b4c5d60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Parent keys used by composite tenant-safe foreign keys.
    for table in ("products", "warehouses", "orders"):
        op.create_unique_constraint(
            f"uq_{table}_organization_id",
            table,
            ["organization_id", "id"],
        )

    for table in ("inventory", "order_items"):
        op.create_unique_constraint(
            f"uq_{table}_organization_id_product",
            table,
            ["organization_id", "id", "product_id"],
        )

    # Uniqueness belongs to a tenant, not to the entire application.
    for table, field in (("products", "sku"), ("warehouses", "name")):
        op.create_unique_constraint(
            f"uq_{table}_organization_{field}",
            table,
            ["organization_id", field],
        )
        op.drop_constraint(
            f"uq_{table}_{field}",
            table,
            type_="unique",
        )

    # Replace single-column foreign keys with tenant-safe composite keys.
    foreign_keys = (
        (
            "inventory", "products",
            ["organization_id", "product_id"],
            ["organization_id", "id"],
            "fk_inventory_product", "RESTRICT",
        ),
        (
            "inventory", "warehouses",
            ["organization_id", "warehouse_id"],
            ["organization_id", "id"],
            "fk_inventory_warehouse", "RESTRICT",
        ),
        (
            "order_items", "orders",
            ["organization_id", "order_id"],
            ["organization_id", "id"],
            "fk_order_items_order", "CASCADE",
        ),
        (
            "order_items", "products",
            ["organization_id", "product_id"],
            ["organization_id", "id"],
            "fk_order_items_product", "RESTRICT",
        ),
        (
            "order_allocations", "order_items",
            ["organization_id", "order_item_id", "product_id"],
            ["organization_id", "id", "product_id"],
            "fk_order_allocation_order_item", "CASCADE",
        ),
        (
            "order_allocations", "inventory",
            ["organization_id", "inventory_id", "product_id"],
            ["organization_id", "id", "product_id"],
            "fk_order_allocation_inventory", "RESTRICT",
        ),
    )

    for table, parent, local_columns, parent_columns, name, ondelete in foreign_keys:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            parent,
            local_columns,
            parent_columns,
            ondelete=ondelete,
        )

    # Indexes for order listing and stock lookups/locks by organization.
    op.create_index(
        "ix_orders_organization_created_id",
        "orders",
        ["organization_id", "created_at", "id"],
    )
    op.create_index(
        "ix_inventory_organization_product_lock",
        "inventory",
        ["organization_id", "product_id", "warehouse_id", "id"],
    )
    op.create_index(
        "ix_inventory_organization_warehouse_id",
        "inventory",
        ["organization_id", "warehouse_id", "id"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Automatic downgrade is unsafe: tenant-local SKUs and warehouse "
        "names can collide globally. Write a reviewed reverse migration."
    )
