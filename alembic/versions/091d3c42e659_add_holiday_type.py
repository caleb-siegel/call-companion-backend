"""add_holiday_type

Revision ID: 091d3c42e659
Revises: a77abba702cf
Create Date: 2026-07-03 12:58:33.313857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '091d3c42e659'
down_revision: Union[str, None] = 'a77abba702cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("COMMIT")
        op.execute("ALTER TYPE shifttype ADD VALUE 'HOLIDAY'")


def downgrade() -> None:
    pass
