from sqlalchemy import Column, Integer, String, Date, Boolean, Enum, Float, DateTime
from sqlalchemy.orm import validates, relationship
from app.database import Base
from enum import Enum as PyEnum
from datetime import date, datetime


# Роли пользователей
class UserRole(PyEnum):
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)  # Имя пользователя
    last_name = Column(String, nullable=False)  # Фамилия пользователя
    date_of_birth = Column(Date, nullable=False)  # Дата рождения
    email = Column(String, unique=True, nullable=False)  # Уникальный Email
    phone = Column(String, unique=True, nullable=False)  # Уникальный Телефон
    role = Column(Enum(UserRole), nullable=False)  # Роль ("CLIENT", "TRAINER", "ADMIN")
    whatsapp_number = Column(String, nullable=True)  # Номер WhatsApp (только для клиентов)

    # Поля, специфичные для клиентов (role == CLIENT)
    balance = Column(Float, nullable=True)  # Баланс клиента

    # Поля, специфичные для тренеров (role == TRAINER)
    salary = Column(Float, nullable=True)  # Зарплата тренера
    is_fixed_salary = Column(Boolean, nullable=True)  # Фиксированная зарплата (True/False)

    # Поле для всех пользователей
    is_active = Column(Boolean, default=True)
    is_authenticated_with_google = Column(Boolean, default=True)  # Аутентификация Google (по умолчанию TRUE)

    # Поле статуса
    deactivation_date = Column(DateTime, nullable=True)

    # Relationships
    real_trainings = relationship("RealTraining", back_populates="trainer")

    # Валидация: WhatsApp только для клиентов
    @validates("whatsapp_number")
    def validate_whatsapp_number(self, key, value):
        if not self.role: return value
        if self.role != UserRole.CLIENT and value is not None:
            raise ValueError("Только пользователи с ролью 'CLIENT' могут иметь номер WhatsApp.")
        return value

    # Валидация: зарплата только для тренеров
    @validates("salary", "is_fixed_salary")
    def validate_salary_fields(self, key, value):
        if not self.role: return value
        if self.role != UserRole.TRAINER and value is not None:
            raise ValueError(f"Поле {key} доступно только для пользователей с ролью 'TRAINER'.")
        return value

    # Валидация: баланс только для клиентов
    @validates("balance")
    def validate_balance(self, key, value):
        if not self.role: return value
        if self.role != UserRole.CLIENT and value is not None:
            raise ValueError("Только пользователи с ролью 'CLIENT' могут иметь баланс.")
        return value

    # Валидация: активен / неактивен только для клиентов и тренеров
    @validates("is_active")
    def validate_is_active(self, key, value):
        if self.role == UserRole.ADMIN:
            raise ValueError("Поле 'is_active' не применяется для пользователей с ролью 'ADMIN'.")
        return value

    # Валидация: дата рождения не может быть в будущем
    @validates("date_of_birth")
    def validate_birth_date(self, key, value):
        if value > date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return value