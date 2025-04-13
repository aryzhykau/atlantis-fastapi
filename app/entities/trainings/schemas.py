from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# Модель для клиента, привязанного к тренировке
class TrainingClientCreate(BaseModel):
    client_id: int = Field(..., description="ID клиента")
    trial_training: bool = Field(default=False, description="Является ли пробным тренировкой")


# Модель для создания тренировки (включает клиентов)
class TrainingWithClientsCreate(BaseModel):
    trainer_id: int = Field(..., description="ID тренера")
    training_date: datetime = Field(..., description="Дата тренировки")
    training_time: datetime = Field(..., description="Время тренировки")
    training_type_id: int = Field(..., description="ID типа тренировки")
    clients: List[TrainingClientCreate] = Field(..., description="Список клиентов, назначенных на тренировку")

    @property
    def training_datetime(self) -> datetime:
        return datetime.combine(self.training_date.date(), self.training_time.time())

    @field_validator("clients")
    def validate_clients(cls, clients):
        if not clients:
            raise ValueError("Тренировка должна содержать хотя бы одного клиента.")
        return clients




class TrainingClientObjectRead(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    birth_date: datetime

    model_config = {"from_attributes": True}

class TrainingClientRead(BaseModel):
    trial_training: bool
    invoice_id: Optional[int]
    is_birthday: bool
    client: TrainingClientObjectRead

    model_config = {"from_attributes": True}



class TrainingWithClientsRead(BaseModel):
    id: int
    trainer_id: int
    training_type_id: int
    training_datetime: datetime
    clients: List[TrainingClientRead]
    model_config = {"from_attributes": True}

