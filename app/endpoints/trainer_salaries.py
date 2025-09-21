
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from app import crud
from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.trainer_training_type_salary import (
    TrainerTrainingTypeSalaryCreate,
    TrainerTrainingTypeSalaryResponse,
    TrainerTrainingTypeSalaryUpdate,
    TrainerSalaryPreviewResponse,
    SalaryFinalizationResponse,
)
from app.schemas.user import UserRole
from app.services.trainer_salary import TrainerSalaryService

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


# New endpoints for cancellation-based salary logic

@router.get(
    "/trainers/{trainer_id}/salary-summary",
    summary="Get trainer salary summary for a period"
)
def get_trainer_salary_summary(
    trainer_id: int,
    start_date: date = Query(..., description="Start date for salary period"),
    end_date: date = Query(..., description="End date for salary period"),
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Get trainer salary summary for a specific period.
    
    Shows:
    - Fixed salary information
    - Individual training payments
    - Total compensation breakdown
    """
    
    # Trainers can only view their own salary
    if current_user["role"] == UserRole.TRAINER and current_user["id"] != trainer_id:
        raise HTTPException(
            status_code=403,
            detail="Trainers can only view their own salary information"
        )
    
    service = TrainerSalaryService(db)
    
    try:
        # Convert dates to datetime for the service
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        summary = service.get_trainer_salary_summary(
            trainer_id=trainer_id,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        return summary
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving salary summary: {str(e)}")


@router.get(
    "/trainers/{trainer_id}/salary/preview",
    response_model=TrainerSalaryPreviewResponse,
    summary="Get a real-time preview of a trainer's daily salary",
)
def get_trainer_salary_preview(
    trainer_id: int,
    preview_date: date = Query(..., description="Date to preview the salary for"),
    current_user: dict = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db),
):
    """
    Get a real-time, non-binding preview of a trainer's salary for a specific day.

    - For **per-training** salary trainers, this calculates potential earnings based on
      all trainings for the day that are marked as `trainer_salary_eligible`.
    - For **fixed-salary** trainers, this simply shows their fixed salary status.
    - This endpoint **does not** create any financial records (expenses).
    """
    if current_user["role"] == UserRole.TRAINER and current_user["id"] != trainer_id:
        raise HTTPException(
            status_code=403,
            detail="Trainers can only view their own salary information",
        )

    service = TrainerSalaryService(db)
    try:
        preview_data = service.get_trainer_salary_preview(
            trainer_id=trainer_id, preview_date=preview_date
        )
        return preview_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating salary preview: {str(e)}"
        )


@router.post(
    "/system/salaries/finalize",
    response_model=SalaryFinalizationResponse,
    summary="Finalize trainer salaries for a specific date",
)
def finalize_trainer_salaries(
    processing_date: date = Query(..., description="The date to process salaries for"),
    current_user: dict = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db),
):
    """
    Finalizes all per-training salaries for a given date.

    This is a system-level endpoint intended to be called by a scheduled job.
    It iterates through all eligible trainings for the day, creates the official
    `Expense` records, and marks the trainings as processed.
    """
    service = TrainerSalaryService(db)
    try:
        result = service.finalize_salaries_for_date(
            processing_date=processing_date, processed_by_id=current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error during salary finalization: {str(e)}"
        )


@router.post(
    "/trainings/{training_id}/calculate-salary",
    summary="Calculate trainer salary for training cancellation"
)
def calculate_training_salary(
    training_id: int,
    cancelled_student_id: int,
    cancellation_time: datetime,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Calculate trainer salary eligibility for a specific training cancellation.
    
    This is a preview/calculation endpoint that doesn't create actual expenses.
    Useful for testing the salary logic.
    """
    
    service = TrainerSalaryService(db)
    
    try:
        # Get training to build training datetime
        from app.crud import real_training as real_training_crud
        training = real_training_crud.get_real_training(db, training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
            
        training_datetime = datetime.combine(training.training_date, training.start_time)
        
        # Calculate salary decision without creating expenses
        salary_decision = service.financial_service.calculate_trainer_salary_for_cancellation(
            training_id=training_id,
            cancelled_student_id=cancelled_student_id,
            cancellation_time=cancellation_time,
            training_start_datetime=training_datetime
        )
        
        # Get trainer salary amount for context
        trainer_salary = service._get_trainer_training_salary(training.responsible_trainer_id, training_id)
        
        return {
            "training_id": training_id,
            "trainer_id": training.responsible_trainer_id,
            "cancelled_student_id": cancelled_student_id,
            "cancellation_time": cancellation_time,
            "training_datetime": training_datetime,
            "salary_decision": salary_decision,
            "potential_salary_amount": trainer_salary,
            "would_create_expense": salary_decision["should_receive_salary"] and trainer_salary > 0
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating salary: {str(e)}")
