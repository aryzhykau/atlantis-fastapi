
from pydantic import BaseModel


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
