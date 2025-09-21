"""
Trainer Salary Service

Handles trainer salary calculations and payments based on training cancellations and completions.
"""

import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.crud import real_training as real_training_crud
from app.crud import user as user_crud
from app.crud import trainer_training_type_salary as trainer_training_type_salary_crud
from app.services.financial import FinancialService
from app.models.real_training import RealTraining

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
        Process trainer salary eligibility when a student cancels.

        This method determines if a trainer should still receive a salary
        after a cancellation and updates the `trainer_salary_eligible` flag
        on the training. It does NOT create an expense record.

        Args:
            training_id: ID of the training
            cancelled_student_id: ID of the cancelled student
            cancellation_time: When the cancellation was made
            processed_by_id: ID of user processing the cancellation

        Returns:
            Dictionary with the outcome of the salary eligibility decision.
        """
        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            raise ValueError("Training not found")

        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)

        if cancellation_time.tzinfo is None:
            cancellation_time = cancellation_time.replace(tzinfo=timezone.utc)

        # Determine if the trainer should still be paid
        salary_decision = self.financial_service.calculate_trainer_salary_for_cancellation(
            training_id=training_id,
            cancelled_student_id=cancelled_student_id,
            cancellation_time=cancellation_time,
            training_start_datetime=training_datetime
        )

        # Update the training record with the eligibility decision
        should_receive_salary = salary_decision["should_receive_salary"]
        self.update_training_salary_eligibility(
            training_id=training_id,
            eligible=should_receive_salary,
            reason=f"Eligibility set to {should_receive_salary} due to student cancellation by user {processed_by_id}"
        )

        logger.info(
            f"Processed cancellation for training {training_id}. "
            f"Trainer salary eligibility set to: {should_receive_salary}. "
            f"Reason: {salary_decision['reason']}"
        )

        # Return a summary of the decision
        return {
            "training_id": training_id,
            "trainer_id": training.responsible_trainer_id,
            "salary_decision": salary_decision,
            "eligibility_updated": True
        }

    def _get_trainer_training_salary(self, trainer_id: int, training_id: int) -> float:
        """
        Get the salary amount for a trainer for a specific training type.

        This function retrieves the specific salary defined for a trainer
        for a particular training type from the TrainerTrainingTypeSalary model.
        """
        trainer = user_crud.get_user_by_id(self.db, trainer_id)
        if not trainer or trainer.role.value != "TRAINER":
            return 0.0

        # If trainer has fixed salary, they don't get individual training payments
        if trainer.is_fixed_salary:
            return 0.0

        # Get the RealTraining to determine the training_type_id
        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            logger.warning(f"Training with ID {training_id} not found for salary calculation.")
            return 0.0

        # Get the specific salary for this trainer and training type
        specific_salary = trainer_training_type_salary_crud.get_trainer_training_type_salary_by_trainer_and_type(
            self.db, trainer_id=trainer_id, training_type_id=training.training_type_id
        )

        if specific_salary:
            return specific_salary.salary
        else:
            logger.info(f"No specific salary found for trainer {trainer_id} and training type {training.training_type_id}. Returning 0.0.")
            return 0.0

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

    def get_trainer_salary_preview(
        self, trainer_id: int, preview_date: date
    ) -> Dict[str, Any]:
        """
        Calculates a non-binding salary preview for a trainer for a specific day.

        This method sums the potential salary from all trainings on a given day
        where the `trainer_salary_eligible` flag is True. It does not read
        from expenses and does not create any database records.

        Args:
            trainer_id: The ID of the trainer.
            preview_date: The date for which to preview the salary.

        Returns:
            A dictionary containing the salary preview details.
        """
        trainer = user_crud.get_user_by_id(self.db, trainer_id)
        if not trainer or trainer.role.value != "TRAINER":
            raise ValueError("Trainer not found")

        if trainer.is_fixed_salary:
            return {
                "trainer_id": trainer_id,
                "preview_date": preview_date,
                "is_fixed_salary": True,
                "fixed_salary_amount": trainer.salary,
                "potential_total_amount": 0,
                "eligible_trainings": [],
            }

        eligible_trainings = real_training_crud.get_real_trainings_by_trainer_and_date(
            self.db, trainer_id=trainer_id, target_date=preview_date
        )

        potential_earnings = []
        total_amount = 0.0

        for training in eligible_trainings:
            if training.trainer_salary_eligible:
                salary_for_training = self._get_trainer_training_salary(
                    trainer_id=trainer_id, training_id=training.id
                )
                if salary_for_training > 0:
                    total_amount += salary_for_training
                    potential_earnings.append(
                        {
                            "training_id": training.id,
                            "training_name": training.training_type.name,
                            "start_time": training.start_time,
                            "potential_amount": salary_for_training,
                        }
                    )

        return {
            "trainer_id": trainer_id,
            "preview_date": preview_date,
            "is_fixed_salary": False,
            "fixed_salary_amount": None,
            "potential_total_amount": total_amount,
            "eligible_trainings": potential_earnings,
        }

    def finalize_salaries_for_date(self, processing_date: date, processed_by_id: int) -> Dict[str, Any]:
        """
        Finalizes trainer salaries for a given date by creating expense records.

        This method should be run by a scheduled job at the end of the day.
        It finds all trainings that are eligible for salary payment but have not
        been processed yet, creates an Expense for each, and marks them as processed.

        Args:
            processing_date: The date for which to process salaries.
            processed_by_id: The ID of the user or system process initiating this.

        Returns:
            A summary of the finalization process.
        """
        trainings_on_date = real_training_crud.get_real_trainings_by_date(
            self.db, date=processing_date
        )

        processed_count = 0
        total_salary_paid = 0.0
        processed_trainings = []

        for training in trainings_on_date:
            if training.trainer_salary_eligible and not training.is_salary_processed:
                trainer_id = training.responsible_trainer_id
                
                trainer = user_crud.get_user_by_id(self.db, trainer_id)
                if not trainer or trainer.is_fixed_salary:
                    # Skip fixed salary trainers or if trainer not found
                    training.is_salary_processed = True # Mark as processed to avoid re-checking
                    continue

                salary_amount = self._get_trainer_training_salary(
                    trainer_id=trainer_id, training_id=training.id
                )

                if salary_amount > 0:
                    self.financial_service.create_trainer_salary_expense(
                        trainer_id=trainer_id,
                        training_id=training.id,
                        amount=salary_amount,
                        description=f"Salary for training: {training.training_type.name} on {training.training_date}",
                        created_by_id=processed_by_id,
                    )
                    total_salary_paid += salary_amount
                    processed_trainings.append({
                        "training_id": training.id,
                        "trainer_id": trainer_id,
                        "amount": salary_amount
                    })
                
                training.is_salary_processed = True
                processed_count += 1
        
        if processed_count > 0:
            self.db.commit()
            logger.info(f"Finalized {processed_count} trainings for date: {processing_date}. Total salary paid: {total_salary_paid}")
        else:
            logger.info(f"No trainings to finalize for date: {processing_date}")

        return {
            "processed_date": processing_date,
            "trainings_processed": processed_count,
            "total_salary_paid": total_salary_paid,
            "processed_details": processed_trainings
        }