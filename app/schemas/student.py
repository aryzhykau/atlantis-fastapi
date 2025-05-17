from pydantic import BaseModel, Field
from datetime import date, datetime


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


# Схема для создания студента
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    is_active: bool = True
    client_id: int  # ID клиента (связь с пользователем)


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


# Схема ответа для одного студента
class StudentResponse(StudentBase):
    client: StudentUser  # ID клиента
    active_subscription_id: int | None = None  # ID текущего активного абонемента
    deactivation_date: datetime | None

    model_config = {"from_attributes": True}

