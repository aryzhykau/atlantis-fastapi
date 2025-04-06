from datetime import date, time, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.entities.users.schemas import ClientRead


class BaseTrainingSchema(BaseModel):
    trainer_id: int
    training_date: date
    training_time: time
    training_type_id: int

    class Config:
        orm_mode = True


class TrainingCreateSchema(BaseTrainingSchema):
    pass


class TrainingReadSchema(BaseTrainingSchema):
    id: int
    created_at: datetime


class TrainingSchema(TrainingReadSchema):
    updated_at: datetime


# Модель для клиента, привязанного к тренировке
class TrainingClientCreate(BaseModel):
    client_id: int = Field(..., description="ID клиента")
    invoice_id: Optional[int] = Field(None, description="ID счета/накладной")
    covered_by_subscription: bool = Field(default=False, description="Оплачено ли подпиской")
    trial_training: bool = Field(default=False, description="Является ли пробным тренировкой")


# Модель для создания тренировки (включает клиентов)
class TrainingWithClientsCreate(BaseModel):
    trainer_id: int = Field(..., description="ID тренера")
    training_date: date = Field(..., description="Дата тренировки")
    training_time: time = Field(..., description="Время тренировки")
    training_type_id: int = Field(..., description="ID типа тренировки")
    clients: List[TrainingClientCreate] = Field(..., description="Список клиентов, назначенных на тренировку")

    @field_validator("clients")
    def validate_clients(cls, clients):
        if not clients:
            raise ValueError("Тренировка должна содержать хотя бы одного клиента.")
        return clients

class TrainingClientRead(BaseModel):
    client: ClientRead
    invoice_id: Optional[int]
    covered_by_subscription: bool
    trial_training: bool

    class Config:
        orm_mode = True


class TrainingWithClientsRead(TrainingReadSchema):
    clients: List[TrainingClientRead]
    model_config = {"from_attributes": True}

