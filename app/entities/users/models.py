from enum import Enum
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base


class TrainingTypeEnum(str, Enum):  # Наследуем str, чтобы хранилось как строка
    ClIENT = "client"
    TRAINER = "trainer"
    ADMIN = "admin"


# Основная модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, index=True)
    whatsapp = Column(String, unique=True, nullable=True)
    salary = Column(Integer, nullable=True)
    fixed_salary = Column(Boolean, nullable=True)
    parent_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    google_authenticated = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

    role = Column(SQLEnum(TrainingTypeEnum), nullable=False)  # Может быть "admin", "client", "trainer"



