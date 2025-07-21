"""Seed initial expense types

Revision ID: ffbdbe85c7c2
Revises: c987a79221c2
Create Date: 2025-07-21 15:22:26.486563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffbdbe85c7c2'
down_revision: Union[str, None] = 'c987a79221c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO expense_types (name, description)
        VALUES ('Проход в бассейн', 'Расход за проход тренера в бассейн за день')
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM expense_types WHERE name = 'Проход в бассейн'
    """) 