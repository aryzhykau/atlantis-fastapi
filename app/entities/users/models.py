from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base


class UserRoleEnum(str, Enum):  # Наследуем str, чтобы хранилось как строка
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"





# Основная модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, index=True)
    whatsapp = Column(String, nullable=True)
    salary = Column(Integer, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    is_client = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    fixed_salary = Column(Boolean, nullable=True)
    balance = Column(Integer, nullable=True)
    google_authenticated = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    payments = relationship("Payment", back_populates="client", lazy="joined")

    clients = relationship("Client", back_populates="User")
    role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"
    ), nullable=False)  # Может быть "admin", "client", "trainer"



