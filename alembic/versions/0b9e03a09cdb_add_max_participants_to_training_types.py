"""add_max_participants_to_training_types

Revision ID: 0b9e03a09cdb
Revises: 6008908f4c87
Create Date: 2025-06-05 14:24:48.573331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b9e03a09cdb'
down_revision: Union[str, None] = '6008908f4c87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
