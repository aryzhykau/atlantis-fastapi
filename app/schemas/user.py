from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import date, datetime
from enum import Enum
from app.schemas.student import StudentCreateWithoutClient
import re


class UserRole(str, Enum):
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"


# General base schema (fields for all users)
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
    date_of_birth: date = Field(..., description="Date of birth")
    is_student: bool = False
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    whatsapp_number: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    students: list[StudentCreateWithoutClient] | None = None

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty')
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+', v):
            raise ValueError('Name can only contain letters, spaces, and hyphens')
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
            raise ValueError('Date of birth cannot be in the future')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError('Field cannot be empty')
            if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+', v):
                raise ValueError('Name can only contain letters, spaces, and hyphens')
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
            raise ValueError('Invalid phone number format. Must contain 10 to 15 digits')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty')
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+', v):
            raise ValueError('Name can only contain letters, spaces, and hyphens')
        return v.strip()

    @model_validator(mode='after')
    def validate_salary(self) -> 'TrainerCreate':
        salary = self.salary
        is_fixed = self.is_fixed_salary

        if is_fixed:
            if salary is None or salary == 0:
                raise ValueError('Fixed salary cannot be zero')
        if salary is not None and salary < 0:
            raise ValueError('Salary cannot be negative')
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
    affected_students_count: int | None = Field(None, description="Number of affected students in case of cascading changes")

    model_config = {"from_attributes": True}

class StudentStatusResponse(BaseModel):
    id: int
    is_active: bool
    deactivation_date: datetime | None
    client_status: bool = Field(..., description="Parent client status")

    model_config = {"from_attributes": True}

class UserListResponse(BaseModel):
    """Schema for user list in autocomplete"""
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, min_length=2, max_length=50)
    date_of_birth: date | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    whatsapp_number: str | None = Field(None, min_length=10, max_length=15, pattern=r'^\+?[0-9]{10,15}$')
    balance: float | None = Field(None, ge=0)
    is_active: bool | None = None
    salary: float | None = Field(None, ge=0)
    is_fixed_salary: bool | None = None

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError('Field cannot be empty')
            if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+', v):
                raise ValueError('Name can only contain letters, spaces, and hyphens')
            return v.strip()
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            if not v or not re.match(r'^\+?[0-9]{10,15}$', v):
                raise ValueError('Invalid phone number format. Must contain 10 to 15 digits')
            return v
        return v

    @model_validator(mode='after')
    def validate_salary(self) -> 'UserUpdate':
        salary = self.salary
        is_fixed = self.is_fixed_salary

        if is_fixed is not None and is_fixed:
            if salary is None or salary == 0:
                raise ValueError('Fixed salary cannot be zero')
        if salary is not None and salary < 0:
            raise ValueError('Salary cannot be negative')
        return self
