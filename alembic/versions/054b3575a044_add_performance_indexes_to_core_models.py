"""Add performance indexes to core models

Revision ID: 054b3575a044
Revises: e064b77658d4
Create Date: 2025-07-11 19:54:37.185734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '054b3575a044'
down_revision: Union[str, None] = 'e064b77658d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_template_date', 'real_trainings', ['template_id', 'training_date'], unique=False)
    op.create_index('idx_auto_renew_end_date', 'student_subscriptions', ['is_auto_renew', 'end_date'], unique=False)
    op.create_index(op.f('ix_training_templates_responsible_trainer_id'), 'training_templates', ['responsible_trainer_id'], unique=False)
    op.create_index(op.f('ix_training_templates_training_type_id'), 'training_templates', ['training_type_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_training_templates_training_type_id'), table_name='training_templates')
    op.drop_index(op.f('ix_training_templates_responsible_trainer_id'), table_name='training_templates')
    op.drop_index('idx_auto_renew_end_date', table_name='student_subscriptions')
    op.drop_index('idx_template_date', table_name='real_trainings')
    # ### end Alembic commands ###
