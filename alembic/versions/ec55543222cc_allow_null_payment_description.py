"""allow_null_payment_description

Revision ID: ec55543222cc
Revises: 606903883f5f
Create Date: 2025-05-21 18:36:52.448918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec55543222cc'
down_revision: Union[str, None] = '606903883f5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменяем колонку description, чтобы она допускала NULL значения
    op.alter_column('payments', 'description',
               existing_type=sa.String(),
               nullable=True)


def downgrade() -> None:
    # Возвращаем ограничение NOT NULL
    op.alter_column('payments', 'description',
               existing_type=sa.String(),
               nullable=False)
