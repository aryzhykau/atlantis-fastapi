"""add_admin

Revision ID: d0ab8775e332
Revises: d92d76fbd8a6
Create Date: 2025-03-08 18:36:04.477838

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd0ab8775e332'
down_revision: Union[str, None] = 'd92d76fbd8a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :role, :google_authenticated)
            """
        ).bindparams(
            email="rorychan0697@gmail.com",
            first_name="Андрей",
            last_name="Рыжиков",
            phone="+421940597865",
            role="ADMIN",  # Убедись, что это правильное значение в БД
            google_authenticated=True
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :role, :google_authenticated)
            """
        ).bindparams(
            email="stadnykyuliia78@gmail.com",
            first_name="Юлия",
            last_name="Стадник",
            phone="+421940597866",
            role="ADMIN",  # Убедись, что это правильное значение в БД
            google_authenticated=True
        )
    )

def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email="rorychan0697@gmail.com")
    )
