"""add client_contact_tasks

Revision ID: 1aa1_client_contact_tasks
Revises: e7cb7521d920
Create Date: 2025-08-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1aa1_client_contact_tasks'
down_revision = 'ffbdbe85c7c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'client_contact_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.Enum('NEW_CLIENT', 'RETURNED', name='clientcontactreason'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'DONE', name='clientcontactstatus'), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_client_contact_tasks_id', 'client_contact_tasks', ['id'])


def downgrade() -> None:
    op.drop_index('ix_client_contact_tasks_id', table_name='client_contact_tasks')
    op.drop_table('client_contact_tasks')
    op.execute("DROP TYPE IF EXISTS clientcontactreason")
    op.execute("DROP TYPE IF EXISTS clientcontactstatus")


