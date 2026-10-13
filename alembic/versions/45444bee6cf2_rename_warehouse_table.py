"""rename warehouse table

Revision ID: 45444bee6cf2
Revises: 9c97256d5ec8
Create Date: 2026-10-13 13:32:58.152858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45444bee6cf2'
down_revision: Union[str, Sequence[str], None] = '9c97256d5ec8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("Warehouse", "warehouses")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("warehouses", "Warehouse")
    # ### end Alembic commands ###
