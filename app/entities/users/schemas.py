import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

# Базовая схема пользователя
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    google_authenticated: Optional[bool] = None
    role: str


class UserAuthInfo(UserBase):
    pass



# Схема для чтения пользователя
class ClientBase(UserBase):
    google_authenticated:  bool
    whatsapp: str
    parent_name: str
    birth_date: datetime.date

# Схема администратора
class AdminBase(UserBase):
    pass

class TrainerBase(UserBase):
    salary: int
    fixed_salary: bool

class AdminRead(AdminBase):
    id: int
    class Config:
        orm_mode: True
        from_attributes = True

# Схема клиента
class ClientRead(ClientBase):
    id: int

class TrainerRead(TrainerBase):
    id: int



class TokenData(BaseModel):
    token: str  # Google ID токен, который приходит с фронта
