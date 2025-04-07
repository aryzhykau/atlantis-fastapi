import datetime

from pydantic import BaseModel


class SubscriptionBase(BaseModel):
    title: str
    total_sessions: int
    duration: int# Название типа тренировки
    price: int
    active: bool = True


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionRead(SubscriptionBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}



