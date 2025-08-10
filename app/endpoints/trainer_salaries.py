
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db
from app.schemas.trainer_training_type_salary import (
    TrainerTrainingTypeSalaryCreate,
    TrainerTrainingTypeSalaryResponse,
    TrainerTrainingTypeSalaryUpdate,
)

router = APIRouter()


@router.post(
    "/trainers/{trainer_id}/salaries",
    response_model=TrainerTrainingTypeSalaryResponse,
    summary="Create a specific salary for a trainer and training type",
)
def create_trainer_salary(
    trainer_id: int,
    salary_create: TrainerTrainingTypeSalaryCreate,
    db: Session = Depends(get_db),
):
    if trainer_id != salary_create.trainer_id:
        raise HTTPException(
            status_code=400,
            detail="Trainer ID in path does not match trainer ID in body",
        )
    return crud.trainer_training_type_salary.create_trainer_training_type_salary(
        db, salary_create=salary_create
    )


@router.get(
    "/trainers/{trainer_id}/salaries",
    response_model=list[TrainerTrainingTypeSalaryResponse],
    summary="Get all specific salaries for a trainer",
)
def get_trainer_salaries(trainer_id: int, db: Session = Depends(get_db)):
    return crud.trainer_training_type_salary.get_trainer_training_type_salaries_by_trainer_id(
        db, trainer_id=trainer_id
    )


@router.put(
    "/trainers/salaries/{salary_id}",
    response_model=TrainerTrainingTypeSalaryResponse,
    summary="Update a specific salary",
)
def update_trainer_salary(
    salary_id: int, salary_update: TrainerTrainingTypeSalaryUpdate, db: Session = Depends(get_db)
):
    db_salary = crud.trainer_training_type_salary.update_trainer_training_type_salary(
        db, salary_id=salary_id, salary_update=salary_update
    )
    if not db_salary:
        raise HTTPException(status_code=404, detail="Salary not found")
    return db_salary


@router.delete(
    "/trainers/salaries/{salary_id}",
    status_code=204,
    summary="Delete a specific salary",
)
def delete_trainer_salary(salary_id: int, db: Session = Depends(get_db)):
    crud.trainer_training_type_salary.delete_trainer_training_type_salary(db, salary_id=salary_id)
    return
