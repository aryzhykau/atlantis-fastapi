from pydantic import BaseModel, EmailStr
from datetime import date
from enum import Enum


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
    first_name: str
    last_name: str
    date_of_birth: date
    email: EmailStr
    phone: str
    whatsapp_number: str | None = None
    balance: float | None = 0.0


class ClientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    whatsapp_number: str | None = None
    balance: float | None = None
    is_active: bool | None = None

class ClientResponse(UserBase):
    whatsapp_number: str | None = None
    balance: float | None = None
    is_active: bool | None = None


class TrainerCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    email: EmailStr
    phone: str
    salary: float | None = None
    is_fixed_salary: bool | None = False

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
