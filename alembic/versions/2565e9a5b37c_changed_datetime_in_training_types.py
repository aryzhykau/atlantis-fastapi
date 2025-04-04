"""changed datetime in training_types

Revision ID: 2565e9a5b37c
Revises: d7c8013aa87e
Create Date: 2025-04-05 01:49:10.998190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2565e9a5b37c'
down_revision: Union[str, None] = 'd7c8013aa87e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('training_types', 'created_at',
               existing_type=sa.DATE(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('training_types', 'updated_at',
               existing_type=sa.DATE(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('training_types', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DATE(),
               existing_nullable=False)
    op.alter_column('training_types', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DATE(),
               existing_nullable=False)
    # ### end Alembic commands ###
