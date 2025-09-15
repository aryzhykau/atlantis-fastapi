"""merge heads

Revision ID: a05a539b0fd1
Revises: 1aa1_client_contact_tasks, 6fd235039f71
Create Date: 2025-08-10 20:10:35.496178

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'a05a539b0fd1'
down_revision: Union[str, None] = ('1aa1_client_contact_tasks', '6fd235039f71')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
