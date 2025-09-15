"""merge heads

Revision ID: f82725d541b1
Revises: 20250912_add_is_deleted, 8ac61085c649
Create Date: 2025-09-15 01:07:43.613724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f82725d541b1'
down_revision: Union[str, None] = ('20250912_add_is_deleted', '8ac61085c649')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
