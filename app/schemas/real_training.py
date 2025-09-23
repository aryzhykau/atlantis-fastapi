from datetime import time, date, datetime
from typing import Optional, List
from app.schemas.user import TrainerResponse
from app.schemas.training_type import TrainingTypeResponse
from pydantic import BaseModel, ConfigDict
from app.schemas.real_training_student import RealTrainingStudentResponse, RealTrainingStudentCreate


class StudentCancellationRequest(BaseModel):
    reason: str
    notification_time: datetime  # Время когда студент уведомил об отмене

    model_config = ConfigDict(from_attributes=True)


class RealTrainingBase(BaseModel):
    id: int
    training_date: date
    start_time: time
    trainer: TrainerResponse
    training_type: TrainingTypeResponse
    template_id: Optional[int]
    is_template_based: bool
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RealTrainingCreate(BaseModel):
    training_date: date
    start_time: time
    responsible_trainer_id: int
    training_type_id: int
    template_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RealTrainingUpdate(BaseModel):
    training_date: Optional[date] = None
    start_time: Optional[time] = None
    responsible_trainer_id: Optional[int] = None
    training_type_id: Optional[int] = None
    template_id: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RealTrainingResponse(RealTrainingBase):
    students: List[RealTrainingStudentResponse]


class TrainingCancellationRequest(BaseModel):
    """Схема для отмены тренировки"""
    reason: str
    process_refunds: bool = True  # Нужно ли запускать финансовые процессы


class StudentCancellationResponse(BaseModel):
    """Схема ответа при отмене участия студента"""
    student_cancelled: bool
    trainer_salary_result: dict

    model_config = ConfigDict(from_attributes=True)





class RealTrainingStudentUpdate(BaseModel):
    """Схема для обновления записи студента на тренировку"""
    status: Optional[str] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RealTrainingWithTrialStudentCreate(RealTrainingCreate):
    student_id: int