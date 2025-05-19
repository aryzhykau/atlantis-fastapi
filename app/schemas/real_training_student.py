from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.student import StudentResponse
from app.schemas.user import TrainerResponse
from app.schemas.attendance import AttendanceStatus


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