"""Add description field to payment_history

Revision ID: 9efc80b025ce
Revises: 93b332870135
Create Date: 2025-05-19 20:32:44.380444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9efc80b025ce'
down_revision: Union[str, None] = '93b332870135'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('payment_history', sa.Column('description', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('payment_history', 'description')
    # ### end Alembic commands ###
