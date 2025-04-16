import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.entities.subscriptions.schemas import SubscriptionRead
from app.entities.users.models import UserRoleEnum
from app.entities.clients.schemas import ClientCreate, ClientRead


class UserRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    google_authenticated: bool = True
    role: str

    model_config = {"from_attributes": True}


class ClientUserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    balance: int = 0
    birth_date: datetime.datetime
    google_authenticated: bool = True
    role: str = UserRoleEnum.CLIENT.value
    is_client: bool = True
    clients: list[ClientCreate]


class ClientUserRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    balance: int = 0
    birth_date: datetime.datetime
    google_authenticated: bool = True
    role: str = UserRoleEnum.CLIENT.value
    is_client: bool = True
    clients: list[ClientRead]

    model_config = {"from_attributes": True}


class TrainerUserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    google_authenticated: bool = True
    role: str = UserRoleEnum.TRAINER.value
    active: bool = True
    salary: int
    fixed_salary: bool


class TrainerUserRead(TrainerUserCreate):
    id: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}






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
    has_trial: Optional[bool] = True
    active: Optional[bool] = True
    birth_date: datetime.datetime

class ClientCreate(ClientBase):
    pass

class ClientSubscriptionCreate(BaseModel):

    subscription_id: int
    active: bool = True
    balance: int = 0
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




#
# class ClientUpdate(ClientRead):
#     pass

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
