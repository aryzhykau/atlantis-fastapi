"""add_admin

Revision ID: 9061d3e64b6f
Revises: 9eb9360ae5ec
Create Date: 2025-03-08 18:29:45.770554

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9061d3e64b6f'
down_revision: Union[str, None] = '9eb9360ae5ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :role, :google_authenticated)
            """
        ),
        {
            "email": "rorychan0697@gmail.com",
            "first_name": "Андрей",
            "last_name": "Рыжиков",
            "phone": "+421940597865",
            "role": "admin",  # Убедись, что значение соответствует тому, что хранится в БД
            "google_authenticated": True,
        }
    )

def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": "rorychan0697@gmail.com"}
    )

