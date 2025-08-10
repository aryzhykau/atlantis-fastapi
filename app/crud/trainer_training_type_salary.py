
from sqlalchemy.orm import Session
from app.models.trainer_training_type_salary import TrainerTrainingTypeSalary
from app.schemas.trainer_training_type_salary import (
    TrainerTrainingTypeSalaryCreate,
    TrainerTrainingTypeSalaryUpdate,
)


def create_trainer_training_type_salary(
    db: Session, salary_create: TrainerTrainingTypeSalaryCreate
) -> TrainerTrainingTypeSalary:
    db_salary = TrainerTrainingTypeSalary(**salary_create.dict())
    db.add(db_salary)
    db.commit()
    db.refresh(db_salary)
    return db_salary


def get_trainer_training_type_salary(
    db: Session, salary_id: int
) -> TrainerTrainingTypeSalary | None:
    return (
        db.query(TrainerTrainingTypeSalary)
        .filter(TrainerTrainingTypeSalary.id == salary_id)
        .first()
    )


def get_trainer_training_type_salaries_by_trainer_id(
    db: Session, trainer_id: int
) -> list[TrainerTrainingTypeSalary]:
    return (
        db.query(TrainerTrainingTypeSalary)
        .filter(TrainerTrainingTypeSalary.trainer_id == trainer_id)
        .all()
    )


def update_trainer_training_type_salary(
    db: Session, salary_id: int, salary_update: TrainerTrainingTypeSalaryUpdate
) -> TrainerTrainingTypeSalary | None:
    db_salary = get_trainer_training_type_salary(db, salary_id)
    if db_salary:
        db_salary.salary = salary_update.salary
        db.commit()
        db.refresh(db_salary)
    return db_salary


def delete_trainer_training_type_salary(db: Session, salary_id: int) -> None:
    db_salary = get_trainer_training_type_salary(db, salary_id)
    if db_salary:
        db.delete(db_salary)
        db.commit()
