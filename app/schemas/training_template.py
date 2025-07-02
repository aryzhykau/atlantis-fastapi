from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import time, date, datetime, timedelta
from typing import Optional, List

from app.schemas.student import StudentResponse
from app.schemas.training_type import TrainingTypeResponse
from app.schemas.user import TrainerResponse


# Базовая схема для Training Template
class TrainingTemplateBase(BaseModel):
    id: int
    day_number: int
    start_time: time
    responsible_trainer: TrainerResponse
    training_type: TrainingTypeResponse

    model_config = ConfigDict(from_attributes=True)


# Схема создания Training Template
class TrainingTemplateCreate(BaseModel):
    day_number: int = Field(
        ..., 
        title="День недели", 
        description="Номер дня недели (1-7, где 1 - понедельник)",
        ge=1,
        le=7,
        error_messages={
            "ge": "День недели должен быть от 1 до 7",
            "le": "День недели должен быть от 1 до 7",
            "type": "День недели должен быть числом"
        }
    )
    start_time: time = Field(
        ..., 
        title="Время начала", 
        description="Время начала тренировки в формате ЧЧ:ММ:СС",
        example="10:00:00"
    )
    responsible_trainer_id: int = Field(
        ..., 
        title="ID тренера",
        description="Идентификатор ответственного тренера",
        gt=0,
        error_messages={
            "gt": "ID тренера должен быть положительным числом",
            "type": "ID тренера должен быть числом"
        }
    )
    training_type_id: int = Field(
        ..., 
        title="ID типа тренировки",
        description="Идентификатор типа тренировки",
        gt=0,
        error_messages={
            "gt": "ID типа тренировки должен быть положительным числом",
            "type": "ID типа тренировки должен быть числом"
        }
    )

    @field_validator("start_time")
    def validate_start_time(cls, v: time) -> time:
        if v.second != 0:
            raise ValueError("Время должно быть указано с точностью до минут (например, 10:00:00)")
        
        if v < time(6, 0) or v > time(23, 0):
            raise ValueError("Время тренировки должно быть в интервале с 6:00 до 23:00")
        
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "day_number": 1,
                    "start_time": "10:00:00",
                    "responsible_trainer_id": 1,
                    "training_type_id": 2,
                }
            ]
        }
    )


# Схема обновления Training Template
class TrainingTemplateUpdate(BaseModel):
    day_number: Optional[int] = Field(
        None, 
        ge=1,
        le=7,
        title="День недели",
        description="Номер дня недели (1-7, где 1 - понедельник)",
        error_messages={
            "ge": "День недели должен быть от 1 до 7",
            "le": "День недели должен быть от 1 до 7",
            "type": "День недели должен быть числом"
        }
    )
    start_time: Optional[time] = Field(
        None,
        title="Время начала",
        description="Время начала тренировки в формате ЧЧ:ММ:СС",
        example="11:00:00"
    )
    responsible_trainer_id: Optional[int] = Field(
        None,
        gt=0,
        title="ID тренера",
        description="Идентификатор ответственного тренера",
        error_messages={
            "gt": "ID тренера должен быть положительным числом",
            "type": "ID тренера должен быть числом"
        }
    )
    training_type_id: Optional[int] = Field(
        None,
        gt=0,
        title="ID типа тренировки",
        description="Идентификатор типа тренировки",
        error_messages={
            "gt": "ID типа тренировки должен быть положительным числом",
            "type": "ID типа тренировки должен быть числом"
        }
    )

    @field_validator("start_time")
    def validate_start_time(cls, v: Optional[time]) -> Optional[time]:
        if v is None:
            return v
            
        if v.second != 0:
            raise ValueError("Время должно быть указано с точностью до минут (например, 10:00:00)")
        
        if v < time(6, 0) or v > time(23, 0):
            raise ValueError("Время тренировки должно быть в интервале с 6:00 до 23:00")
        
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "day_number": 2,
                    "start_time": "12:30:00",
                    "responsible_trainer_id": 1,
                    "training_type_id": 1
                }
            ]
        }
    )


# Базовая схема для Training Student Template
class TrainingStudentTemplateBase(BaseModel):
    id: int
    training_template_id: int
    student_id: int
    start_date: date
    is_frozen: bool = False
    freeze_start_date: Optional[date] = None
    freeze_duration_days: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Схема создания Training Student Template
class TrainingStudentTemplateCreate(BaseModel):
    training_template_id: int = Field(
        ...,
        gt=0,
        title="ID шаблона тренировки",
        description="Идентификатор шаблона тренировки",
        error_messages={
            "gt": "ID шаблона тренировки должен быть положительным числом",
            "type": "ID шаблона тренировки должен быть числом"
        }
    )
    student_id: int = Field(
        ...,
        gt=0,
        title="ID студента",
        description="Идентификатор студента",
        error_messages={
            "gt": "ID студента должен быть положительным числом",
            "type": "ID студента должен быть числом"
        }
    )
    start_date: date = Field(
        ...,
        title="Дата начала",
        description="Дата начала тренировок"
    )

    # Убрали валидацию на "не в прошлом" - start_date может быть исторической 
    # для корректной работы генерации тренировок и дублирования шаблонов

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "training_template_id": 1,
                    "student_id": 1,
                    "start_date": "2024-03-20"
                }
            ]
        }
    )


# Схема обновления Training Student Template
class TrainingStudentTemplateUpdate(BaseModel):
    is_frozen: Optional[bool] = Field(
        None,
        title="Статус заморозки",
        description="Флаг заморозки тренировок"
    )
    freeze_start_date: Optional[date] = Field(
        None,
        title="Дата начала заморозки",
        description="Дата начала периода заморозки"
    )
    freeze_duration_days: Optional[int] = Field(
        None,
        gt=0,
        title="Длительность заморозки",
        description="Количество дней заморозки",
        error_messages={
            "gt": "Длительность заморозки должна быть положительным числом",
            "type": "Длительность заморозки должна быть числом"
        }
    )

    @model_validator(mode='after')
    def validate_freeze_fields(self) -> 'TrainingStudentTemplateUpdate':
        if self.is_frozen:
            if not self.freeze_start_date:
                raise ValueError("При заморозке необходимо указать дату начала заморозки")
            if not self.freeze_duration_days:
                raise ValueError("При заморозке необходимо указать длительность заморозки")
            if self.freeze_start_date < date.today():
                raise ValueError("Дата начала заморозки не может быть в прошлом")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "is_frozen": True,
                    "freeze_start_date": "2024-03-25",
                    "freeze_duration_days": 14
                }
            ]
        }
    )


# Схема ответа для Training Student Template
class TrainingStudentTemplateResponse(TrainingStudentTemplateBase):
    student: StudentResponse

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "training_template_id": 1,
                    "student_id": 1,
                    "start_date": "2024-03-20",
                    "is_frozen": False,
                    "freeze_start_date": None,
                    "freeze_duration_days": None,
                    "student": {
                        "id": 1,
                        "name": "Иван Иванов"
                    }
                }
            ]
        }
    )


# Схема ответа для Training Template с привязанными студентами
class TrainingTemplateResponse(TrainingTemplateBase):
    assigned_students: List[TrainingStudentTemplateResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "day_number": 1,
                    "start_time": "10:00:00",
                    "responsible_trainer": {
                        "id": 1,
                        "name": "Петр Петров"
                    },
                    "training_type": {
                        "id": 2,
                        "name": "Йога"
                    },
                    "assigned_students": [
                        {
                            "id": 1,
                            "training_template_id": 1,
                            "student_id": 1,
                            "start_date": "2024-03-20",
                            "is_frozen": False,
                            "freeze_start_date": None,
                            "freeze_duration_days": None,
                            "student": {
                                "id": 1,
                                "name": "Иван Иванов"
                            }
                        }
                    ]
                }
            ]
        }
    )