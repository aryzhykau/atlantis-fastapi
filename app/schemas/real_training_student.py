from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator

from app.models.real_training import AttendanceStatus
from app.schemas.student import StudentResponse


class RealTrainingStudentCreate(BaseModel):
    student_id: int
    template_student_id: Optional[int] = None
    is_trial: bool = False


class RealTrainingStudentUpdate(BaseModel):
    status: Optional[AttendanceStatus] = Field(None, description="Статус посещения")
    cancellation_reason: Optional[str] = Field(None, description="Причина отмены")

    @validator("status")
    def prevent_present_status(cls, v):
        if v == AttendanceStatus.PRESENT:
            raise ValueError(
                "Cannot manually set status to PRESENT. It is handled automatically."
            )
        return v

    class Config:
        from_attributes = True


from app.schemas.student import StudentResponse

class RealTrainingStudentResponse(BaseModel):
    real_training_id: int
    student_id: int
    status: Optional[AttendanceStatus] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    attendance_marked_at: Optional[datetime] = None
    student: Optional[StudentResponse] = None
    is_trial: bool

    class Config:
        from_attributes = True 