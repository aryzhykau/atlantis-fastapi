import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.entities.subscriptions.schemas import SubscriptionRead


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

class ClientSubscriptionCreate(BaseModel):

    subscription_id: int
    active: bool = True
    start_date: datetime.datetime = datetime.datetime.today()
    end_date: Optional[datetime.datetime] = None


class ClientSubscriptionRead(BaseModel):
    active: bool
    is_active: bool
    start_date: datetime.datetime
    end_date: datetime.datetime
    id: int
    sessions_left: int
    subscription: SubscriptionRead
    model_config = {"from_attributes": True}



class ClientRead(ClientBase):
    id: int
    created_at: datetime.datetime
    active_subscription: Optional[ClientSubscriptionRead] = None
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
