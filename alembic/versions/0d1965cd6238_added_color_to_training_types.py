"""added color to training types

Revision ID: 0d1965cd6238
Revises: 937d9bda9a5b
Create Date: 2025-04-13 00:16:04.723951

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '0d1965cd6238'
down_revision: Union[str, None] = '937d9bda9a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('training_types', sa.Column('color', sa.String(), server_default='#FFFFFF', nullable=False))
    connection = op.get_bind()
    connection.execute(text("""
           UPDATE training_types
           SET color = '#FFFFFF'
           WHERE color IS NULL
       """))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('training_types', 'color')
    # ### end Alembic commands ###
