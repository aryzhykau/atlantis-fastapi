from pydantic import BaseModel, EmailStr, Field, validator, field_validator, model_validator
from datetime import date, datetime
from enum import Enum
from app.schemas.student import StudentCreateWithoutClient
import re


class UserRole(str, Enum):
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"


# Общая базовая схема (поля для всех пользователей)
class UserBase(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: date
    email: EmailStr
    phone: str
    role: UserRole
    is_authenticated_with_google: bool

    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    date_of_birth: date = Field(..., description="Дата рождения")
    is_student: bool = False
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    whatsapp_number: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    students: list[StudentCreateWithoutClient] | None = None

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError('Дата рождения не может быть в будущем')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Поле не может быть пустым')
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+$', v):
            raise ValueError('Имя может содержать только буквы, пробелы и дефис')
        return v.strip()


class ClientUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, min_length=2, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    whatsapp_number: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    balance: float | None = Field(None, ge=0)
    is_active: bool | None = None
    date_of_birth: date | None = None

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError('Дата рождения не может быть в будущем')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError('Поле не может быть пустым')
            if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+$', v):
                raise ValueError('Имя может содержать только буквы, пробелы и дефис')
            return v.strip()
        return v

class ClientResponse(UserBase):
    whatsapp_number: str | None = None
    balance: float | None = None
    is_active: bool | None = None


class TrainerCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    date_of_birth: date
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    salary: float | None = Field(None, ge=0)
    is_fixed_salary: bool = False

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v or not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Неверный формат номера телефона. Должен содержать от 10 до 15 цифр')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError('Дата рождения не может быть в будущем')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Поле не может быть пустым')
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+$', v):
            raise ValueError('Имя может содержать только буквы, пробелы и дефис')
        return v.strip()

    @model_validator(mode='after')
    def validate_salary(self) -> 'TrainerCreate':
        salary = self.salary
        is_fixed = self.is_fixed_salary

        if is_fixed:
            if salary is None or salary == 0:
                raise ValueError('Фиксированная зарплата не может быть нулевой')
        if salary is not None and salary < 0:
            raise ValueError('Зарплата не может быть отрицательной')
        return self

class TrainerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    salary: float | None = None
    is_fixed_salary: bool | None = None
    is_active: bool | None = None

class TrainerResponse(UserBase):
    salary: float | None = None
    is_fixed_salary: bool | None = None
    is_active: bool | None = None
    deactivation_date: datetime | None = None

class TrainersList(BaseModel):
    trainers: list[TrainerResponse]

class UserDelete(BaseModel):
    id: int

class UserMe(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    role: UserRole

class StatusUpdate(BaseModel):
    is_active: bool

class ClientStatusResponse(BaseModel):
    id: int
    is_active: bool
    deactivation_date: datetime | None
    affected_students_count: int | None = Field(None, description="Количество затронутых студентов при каскадном изменении")

    model_config = {"from_attributes": True}

class StudentStatusResponse(BaseModel):
    id: int
    is_active: bool
    deactivation_date: datetime | None
    client_status: bool = Field(..., description="Статус родительского клиента")

    model_config = {"from_attributes": True}
