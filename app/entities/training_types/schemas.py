import datetime

from pydantic import BaseModel
from typing import Optional


class TrainingTypeBase(BaseModel):
    title: str # Название типа тренировки
    require_subscription: bool
    price: int


class TrainingTypeCreate(TrainingTypeBase):
    pass


class TrainingTypeRead(TrainingTypeBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}



