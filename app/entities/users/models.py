from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum

from app.database import Base


class UserRoleEnum(str, Enum):  # Наследуем str, чтобы хранилось как строка
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"



# Основная модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, index=True)
    whatsapp = Column(String, nullable=True)
    salary = Column(Integer, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    fixed_salary = Column(Boolean, nullable=True)
    parent_name = Column(String, nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    google_authenticated = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

    role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"
    ), nullable=False)  # Может быть "admin", "client", "trainer"



