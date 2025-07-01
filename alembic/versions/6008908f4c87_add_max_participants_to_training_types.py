"""add_max_participants_to_training_types

Revision ID: 6008908f4c87
Revises: 8a1341eac169
Create Date: 2025-06-05 14:17:42.639471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6008908f4c87'
down_revision: Union[str, None] = '8a1341eac169'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
