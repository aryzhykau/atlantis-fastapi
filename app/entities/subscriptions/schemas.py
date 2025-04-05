import datetime

from pydantic import BaseModel


class SubscriptionBase(BaseModel):
    title: str
    total_sessions: int # Название типа тренировки
    price: int


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionRead(SubscriptionBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}



