"""change_whatsapp_unique

Revision ID: 42a728f4223f
Revises: d0ab8775e332
Create Date: 2025-03-11 23:19:47.592731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42a728f4223f'
down_revision: Union[str, None] = 'd0ab8775e332'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('users_whatsapp_key', 'users', type_='unique')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('users_whatsapp_key', 'users', ['whatsapp'])
    # ### end Alembic commands ###
