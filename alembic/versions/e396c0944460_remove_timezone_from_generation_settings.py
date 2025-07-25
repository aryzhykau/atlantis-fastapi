"""remove timezone from generation settings

Revision ID: e396c0944460
Revises: 50d1ad23c6ce
Create Date: 2025-05-17 14:18:08.035242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e396c0944460'
down_revision: Union[str, None] = '50d1ad23c6ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('generation_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('generation_day', sa.Integer(), nullable=False),
    sa.Column('generation_time', sa.Time(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('last_generation', sa.DateTime(), nullable=True),
    sa.Column('next_generation', sa.DateTime(), nullable=True),
    sa.Column('safe_cancellation_hours', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generation_settings_id'), 'generation_settings', ['id'], unique=False)
    op.create_table('real_trainings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('training_date', sa.Date(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('responsible_trainer_id', sa.Integer(), nullable=False),
    sa.Column('training_type_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('is_template_based', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.Column('cancellation_reason', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['responsible_trainer_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['template_id'], ['training_templates.id'], ),
    sa.ForeignKeyConstraint(['training_type_id'], ['training_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_real_trainings_id'), 'real_trainings', ['id'], unique=False)
    op.create_table('real_training_students',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('real_training_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('template_student_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('PRESENT', 'ABSENT', 'LATE', 'CANCELLED', name='attendancestatus'), nullable=True),
    sa.Column('notification_time', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.Column('cancellation_reason', sa.String(), nullable=True),
    sa.Column('attendance_marked_at', sa.DateTime(), nullable=True),
    sa.Column('attendance_marked_by_id', sa.Integer(), nullable=True),
    sa.Column('requires_payment', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['attendance_marked_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['real_training_id'], ['real_trainings.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.ForeignKeyConstraint(['template_student_id'], ['training_client_templates.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_real_training_students_id'), 'real_training_students', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_real_training_students_id'), table_name='real_training_students')
    op.drop_table('real_training_students')
    op.drop_index(op.f('ix_real_trainings_id'), table_name='real_trainings')
    op.drop_table('real_trainings')
    op.drop_index(op.f('ix_generation_settings_id'), table_name='generation_settings')
    op.drop_table('generation_settings')
    # ### end Alembic commands ###
