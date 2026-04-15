"""add_schedule_confirmed_and_trial_fields

Revision ID: 307c1eed5b0c
Revises: 82747771ed7b
Create Date: 2026-04-06 15:00:34.895710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '307c1eed5b0c'
down_revision: Union[str, None] = '82747771ed7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('student_subscriptions', sa.Column('schedule_confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('students', sa.Column('trial_used_at', sa.DateTime(), nullable=True))
    op.add_column('students', sa.Column('trial_real_training_student_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_students_trial_rts', 'students', 'real_training_students', ['trial_real_training_student_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_students_trial_rts', 'students', type_='foreignkey')
    op.drop_column('students', 'trial_real_training_student_id')
    op.drop_column('students', 'trial_used_at')
    op.drop_column('student_subscriptions', 'schedule_confirmed_at')
