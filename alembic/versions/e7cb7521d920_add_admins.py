"""add admins

Revision ID: e7cb7521d920
Revises: 2a85d3731dd2
Create Date: 2025-05-13 15:35:02.100539
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Boolean, Date, Enum, Float
from app.models.user import UserRole  # Используем Enum UserRole из существующей модели

# revision identifiers, used by Alembic.
revision: str = 'e7cb7521d920'
down_revision: Union[str, None] = '2a85d3731dd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    users_table = table(
        "users",
        column("id", Integer),  # ID (автоинкремент)
        column("first_name", String),
        column("last_name", String),
        column("date_of_birth", Date),
        column("email", String),
        column("phone", String),
        column("role", Enum(UserRole)),
        column("is_active", Boolean),
        column("is_authenticated_with_google", Boolean),
    )

    # Добавляем одного или нескольких пользователей-администраторов
    op.bulk_insert(
        users_table,
        [
            {
                "first_name": "Андрей",
                "last_name": "Рыжиков",
                "email": "rorychan0697@gmail.com",
                "phone": "0940597865",
                "date_of_birth": "1997-06-14",
                "role": UserRole.ADMIN,
                "is_active": True,
                "is_authenticated_with_google": True,
            },
        ],
    )


def downgrade() -> None:
    # Удаляем добавленных администраторов, основанных на их email
    op.execute(
        """
        DELETE FROM users
        WHERE email IN ('rorychan0697@gmail.com')
        """
    )