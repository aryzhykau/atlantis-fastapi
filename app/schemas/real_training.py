from datetime import time, date, datetime
from typing import Optional, List
from app.schemas.user import TrainerResponse
from app.schemas.training_type import TrainingTypeResponse
from app.schemas.training_template import TrainingTemplateResponse
from app.schemas.student import StudentResponse
from enum import Enum
from pydantic import BaseModel, ConfigDict


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    CANCELLED = "cancelled"


class RealTrainingBase(BaseModel):
    id: int
    training_date: date
    start_time: time
    trainer: TrainerResponse
    training_type: TrainingTypeResponse
    is_template_based: bool
    template: Optional[TrainingTemplateResponse] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

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
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RealTrainingStudentBase(BaseModel):
    id: int
    real_training_id: int
    student: StudentResponse
    status: Optional[AttendanceStatus]
    notification_time: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    attendance_marked_at: Optional[datetime]
    attendance_marked_by: Optional[TrainerResponse]
    requires_payment: bool

    model_config = ConfigDict(from_attributes=True)


class RealTrainingStudentCreate(BaseModel):
    student_id: int
    template_student_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RealTrainingStudentUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    notification_time: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RealTrainingStudentResponse(RealTrainingStudentBase):
    pass


class RealTrainingResponse(RealTrainingBase):
    students: List[RealTrainingStudentResponse] 