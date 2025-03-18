import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

# Базовая схема пользователя
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    google_authenticated: bool = True
    role: str


class UserAuthInfo(UserBase):
    pass



# Схема для чтения пользователя
class ClientBase(UserBase):
    whatsapp: Optional[str] = None
    parent_name: Optional[str] = None
    active: Optional[bool] = True
    birth_date: datetime.datetime

class ClientCreate(ClientBase):
    pass



class ClientRead(ClientBase):
    id: int
    created_at: datetime.datetime
    model_config = {"from_attributes": True}

class ClientUpdate(ClientRead):
    pass


# Схема администратора
class AdminBase(UserBase):
    pass

class AdminRead(AdminBase):
    id: int
    model_config = {"from_attributes": True}


class TrainerBase(UserBase):
    active: bool = True
    salary: int
    fixed_salary: bool

class TrainerCreate(TrainerBase):
    pass

class TrainerRead(TrainerBase):
    id: int
    created_at: datetime.datetime
    model_config = {"from_attributes": True}

class TrainerUpdate(TrainerRead):
    pass

class TokenData(BaseModel):
    token: str  # Google ID токен, который приходит с фронта
