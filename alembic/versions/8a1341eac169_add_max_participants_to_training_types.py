"""\add_max_participants_to_training_types\

Revision ID: 8a1341eac169
Revises: 223cc5fe592e
Create Date: 2025-06-05 14:11:05.831674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a1341eac169'
down_revision: Union[str, None] = '223cc5fe592e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
