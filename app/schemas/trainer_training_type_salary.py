from pydantic import BaseModel
from datetime import date, time
from typing import List, Optional


class TrainerTrainingTypeSalaryBase(BaseModel):
    trainer_id: int
    training_type_id: int
    salary: float


class TrainerTrainingTypeSalaryCreate(TrainerTrainingTypeSalaryBase):
    pass


class TrainerTrainingTypeSalaryUpdate(BaseModel):
    salary: float


class TrainerTrainingTypeSalaryResponse(TrainerTrainingTypeSalaryBase):
    id: int

    class Config:
        orm_mode = True


class SalaryPreviewTraining(BaseModel):
    training_id: int
    training_name: str
    start_time: time
    potential_amount: float


class TrainerSalaryPreviewResponse(BaseModel):
    trainer_id: int
    preview_date: date
    is_fixed_salary: bool
    fixed_salary_amount: Optional[float] = None
    potential_total_amount: float
    eligible_trainings: List[SalaryPreviewTraining]

    class Config:
        orm_mode = True


class SalaryFinalizationResponse(BaseModel):
    processed_date: date
    trainings_processed: int
    total_salary_paid: float

