"""Add deactivation_date field

Revision ID: 1f12ef6834bf
Revises: 4ce79f7f7d75
Create Date: 2025-05-17 00:16:53.339380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f12ef6834bf'
down_revision: Union[str, None] = '4ce79f7f7d75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('students', sa.Column('deactivation_date', sa.DateTime(), nullable=True))
    op.drop_constraint('students_client_id_fkey', 'students', type_='foreignkey')
    op.create_foreign_key(None, 'students', 'users', ['client_id'], ['id'], ondelete='CASCADE')
    op.add_column('users', sa.Column('deactivation_date', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'deactivation_date')
    op.drop_constraint(None, 'students', type_='foreignkey')
    op.create_foreign_key('students_client_id_fkey', 'students', 'users', ['client_id'], ['id'])
    op.drop_column('students', 'deactivation_date')
    # ### end Alembic commands ###
