import datetime

from pydantic import BaseModel


class TrainingTypeBase(BaseModel):
    title: str # Название типа тренировки
    require_subscription: bool
    color: str
    price: int


class TrainingTypeCreate(TrainingTypeBase):
    pass


class TrainingTypeRead(TrainingTypeBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}



