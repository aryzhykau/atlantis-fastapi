"""
Trainer Salary Service

Handles trainer salary calculations and payments based on training cancellations and completions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.crud import real_training as real_training_crud
from app.crud import user as user_crud
from app.services.financial import FinancialService
from app.models.real_training import AttendanceStatus
from app.schemas.expense import ExpenseCreate

logger = logging.getLogger(__name__)


class TrainerSalaryService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)

    def process_student_cancellation_salary(
        self,
        training_id: int,
        cancelled_student_id: int,
        cancellation_time: datetime,
        processed_by_id: int
    ) -> Dict[str, Any]:
        """
        Process trainer salary when a student cancels.
        
        Args:
            training_id: ID of the training
            cancelled_student_id: ID of the cancelled student
            cancellation_time: When the cancellation was made
            processed_by_id: ID of user processing the cancellation
            
        Returns:
            Dictionary with salary decision and details
        """
        
        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            raise ValueError("Training not found")
            
        # Combine training date and time for accurate calculation
        # Make it timezone-aware to match cancellation_time
        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
            
        # Ensure cancellation_time is also timezone-aware
        if cancellation_time.tzinfo is None:
            cancellation_time = cancellation_time.replace(tzinfo=timezone.utc)
        
        # Calculate salary eligibility
        salary_decision = self.financial_service.calculate_trainer_salary_for_cancellation(
            training_id=training_id,
            cancelled_student_id=cancelled_student_id,
            cancellation_time=cancellation_time,
            training_start_datetime=training_datetime
        )
        
        result = {
            "training_id": training_id,
            "trainer_id": training.responsible_trainer_id,
            "cancelled_student_id": cancelled_student_id,
            "cancellation_time": cancellation_time,
            "training_datetime": training_datetime,
            "salary_decision": salary_decision,
            "expense_created": False,
            "expense_id": None
        }
        
        # Create expense if trainer should receive salary
        if salary_decision["should_receive_salary"]:
            trainer_salary = self._get_trainer_training_salary(training.responsible_trainer_id, training_id)
            
            if trainer_salary > 0:
                expense = self.financial_service.create_trainer_salary_expense(
                    trainer_id=training.responsible_trainer_id,
                    training_id=training_id,
                    amount=trainer_salary,
                    description=f"Training salary - {salary_decision['reason']} (Training: {training.training_date} {training.start_time})",
                    created_by_id=processed_by_id
                )
                
                result["expense_created"] = True
                result["expense_id"] = expense.id
                result["salary_amount"] = trainer_salary
                
                logger.info(f"Created trainer salary expense: {expense.id} for trainer {training.responsible_trainer_id}, amount: {trainer_salary}")
            else:
                result["salary_amount"] = 0
                logger.info(f"Trainer {training.responsible_trainer_id} salary is 0, no expense created")
        else:
            logger.info(f"Trainer {training.responsible_trainer_id} not eligible for salary: {salary_decision['reason']}")
            
        return result

    def _get_trainer_training_salary(self, trainer_id: int, training_id: int) -> float:
        """
        Get the salary amount for a trainer for a specific training.
        
        This could be based on:
        - Trainer's base salary per training
        - Training type specific salary
        - Number of students
        - etc.
        
        For now, using trainer's base salary field.
        """
        trainer = user_crud.get_user_by_id(self.db, trainer_id)
        if not trainer or trainer.role.value != "TRAINER":
            return 0.0
            
        # If trainer has fixed salary, they don't get individual training payments
        if trainer.is_fixed_salary:
            return 0.0
            
        # Return trainer's per-training salary (assuming this is stored in salary field)
        return trainer.salary if trainer.salary else 0.0

    def update_training_salary_eligibility(
        self, 
        training_id: int, 
        eligible: bool, 
        reason: Optional[str] = None
    ) -> bool:
        """
        Update the trainer_salary_eligible field for a training.
        
        Args:
            training_id: ID of the training
            eligible: Whether trainer is eligible for salary
            reason: Optional reason for the change
            
        Returns:
            True if updated successfully
        """
        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            return False
            
        training.trainer_salary_eligible = eligible
        self.db.commit()
        
        if reason:
            logger.info(f"Updated training {training_id} salary eligibility to {eligible}: {reason}")
        
        return True

    def get_trainer_salary_summary(
        self, 
        trainer_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get a summary of trainer salary for a period.
        
        Args:
            trainer_id: ID of the trainer
            start_date: Start of the period
            end_date: End of the period
            
        Returns:
            Dictionary with salary summary
        """
        # This would aggregate expenses and provide summary
        # Implementation depends on specific business requirements
        
        trainer = user_crud.get_user_by_id(self.db, trainer_id)
        if not trainer:
            raise ValueError("Trainer not found")
            
        # Get trainer salary expenses for the period
        expenses = self.financial_service.get_expenses(
            user_id=trainer_id,
            # Would need to add date filtering to get_expenses method
        )
        
        # Filter by date and trainer salary type
        trainer_salary_expenses = [
            exp for exp in expenses 
            if (exp.expense_type.name == "Trainer Salary" and 
                start_date <= exp.expense_date <= end_date)
        ]
        
        total_individual_salary = sum(exp.amount for exp in trainer_salary_expenses)
        
        return {
            "trainer_id": trainer_id,
            "trainer_name": f"{trainer.first_name} {trainer.last_name}",
            "period": {
                "start": start_date,
                "end": end_date
            },
            "is_fixed_salary": trainer.is_fixed_salary,
            "fixed_salary_amount": trainer.salary if trainer.is_fixed_salary else None,
            "individual_training_payments": {
                "total_amount": total_individual_salary,
                "payment_count": len(trainer_salary_expenses),
                "payments": trainer_salary_expenses
            }
        }