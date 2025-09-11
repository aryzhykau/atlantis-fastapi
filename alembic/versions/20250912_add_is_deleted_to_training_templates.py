"""add is_deleted to training_templates

Revision ID: 20250912_add_is_deleted
Revises: 362b779f497e
Create Date: 2025-09-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250912_add_is_deleted'
down_revision = '362b779f497e'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_deleted column with default False
    op.add_column('training_templates', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # Create index to speed up queries filtering by is_deleted
    op.create_index(op.f('ix_training_templates_is_deleted'), 'training_templates', ['is_deleted'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_training_templates_is_deleted'), table_name='training_templates')
    op.drop_column('training_templates', 'is_deleted')
