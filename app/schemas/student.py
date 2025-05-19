from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.real_training_student import RealTrainingStudentResponse


# Базовая схема (поля для всех студентов)
class StudentBase(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: date
    is_active: bool

    model_config = {"from_attributes": True}


# Схема для создания студента без привязки к клиенту
class StudentCreateWithoutClient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    is_active: bool = True

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v > date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return v


# Схема для создания студента
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    is_active: bool = True
    client_id: int  # ID клиента (связь с пользователем)

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v > date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return v


class StudentUser(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
    balance: float

    model_config = {"from_attributes": True}


# Схема для обновления студента
class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    is_active: bool | None = None
    client_id: int | None = None  # Возможность изменять связь с клиентом

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v and v > date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return v


# Схема ответа для одного студента
class StudentResponse(StudentBase):
    client: StudentUser  # ID клиента
    active_subscription_id: int | None = None  # ID текущего активного абонемента
    deactivation_date: datetime | None

    model_config = {"from_attributes": True}

