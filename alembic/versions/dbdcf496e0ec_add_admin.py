"""add_admin

Revision ID: dbdcf496e0ec
Revises: 3d3752b00c03
Create Date: 2025-04-11 00:25:54.232253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision: str = 'dbdcf496e0ec'
down_revision: Union[str, None] = '3d3752b00c03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, active, created_at, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :active, :created_at, :role, :google_authenticated)
            """
        ).bindparams(
            email="rorychan0697@gmail.com",
            first_name="Андрей",
            last_name="Рыжиков",
            active=True,
            created_at=datetime.datetime.now(),
            phone="+421940597865",
            role="ADMIN",  # Убедись, что это правильное значение в БД
            google_authenticated=True
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, active, created_at, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :active, :created_at, :role, :google_authenticated)
            """
        ).bindparams(
            email="stadnykyuliia78@gmail.com",
            first_name="Юлия",
            active=True,
            last_name="Стадник",
            created_at=datetime.datetime.now(),
            phone="+421940597863",
            role="ADMIN",  # Убедись, что это правильное значение в БД
            google_authenticated=True
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, first_name, last_name, phone, active, created_at, role, google_authenticated)
            VALUES (:email, :first_name, :last_name, :phone, :active, :created_at, :role, :google_authenticated)
            """
        ).bindparams(
            email="l.v.evseeva1@gmail.com",
            first_name="Любовь",
            active=True,
            last_name="Евсеева",
            created_at=datetime.datetime.now(),
            phone="+421940597866",
            role="ADMIN",  # Убедись, что это правильное значение в БД
            google_authenticated=True
        )
    )

def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email="rorychan0697@gmail.com")
    )
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email="stadnykyuliia78@gmail.com")
    )
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email="l.v.evseeva1@gmail.com")
    )