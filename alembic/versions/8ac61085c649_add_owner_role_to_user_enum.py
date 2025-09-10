"""add_owner_role_to_user_enum

Revision ID: 8ac61085c649
Revises: bcd41458ec9d
Create Date: 2025-09-10 10:41:47.926259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ac61085c649'
down_revision: Union[str, None] = 'bcd41458ec9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OWNER to the UserRole enum
    op.execute("ALTER TYPE userrole ADD VALUE 'OWNER'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum and updating all references
    # For now, we'll leave this as a no-op since removing enum values is complex
    pass
