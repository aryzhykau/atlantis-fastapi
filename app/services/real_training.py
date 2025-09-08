import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.crud import real_training as crud
from app.crud import student as student_crud
from app.models import (
    RealTraining,
    RealTrainingStudent,
    Student,
    StudentSubscription,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    User,
    UserRole
)
from app.models.real_training import AttendanceStatus
from app.schemas.real_training import (
    RealTrainingStudentCreate,
    RealTrainingStudentUpdate,
    StudentCancellationRequest,
    TrainingCancellationRequest
)

from app.database import transactional
from app.services.financial import FinancialService
from app.services.subscription import SubscriptionService
from app.services.trainer_salary import TrainerSalaryService
from app.errors.real_training_errors import (
    RealTrainingError,
    TrainingNotFound,
    StudentNotOnTraining,
    StudentAlreadyRegistered,
    StudentInactive,
    SubscriptionRequired,
    InsufficientSessions
)
from app.schemas.invoice import InvoiceCreate

logger = logging.getLogger(__name__)

# Константы для логики отмен
SAFE_CANCELLATION_HOURS = 12  # Часов до тренировки для безопасной отмены

class RealTrainingService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)
        self.subscription_service = SubscriptionService(db)
        self.trainer_salary_service = TrainerSalaryService(db)

    # --- Public Methods (Transactional) ---

    def cancel_student(
        self,
        training_id: int,
        student_id: int,
        cancellation_data: StudentCancellationRequest,
        processed_by_id: int
    ) -> dict:
        """
        Отмена участия студента в тренировке
        """
        with transactional(self.db) as session:
            self._cancel_student_logic(session, training_id, student_id, cancellation_data)
            
            # Process trainer salary after student cancellation
            salary_result = self.trainer_salary_service.process_student_cancellation_salary(
                training_id=training_id,
                cancelled_student_id=student_id,
                cancellation_time=cancellation_data.notification_time,
                processed_by_id=processed_by_id
            )
            
            return {
                "student_cancelled": True,
                "trainer_salary_result": salary_result
            }

    def cancel_training(
        self,
        training_id: int,
        cancellation_data: TrainingCancellationRequest
    ) -> RealTraining:
        """
        Отмена всей тренировки
        """
        with transactional(self.db) as session:
            return self._cancel_training_logic(session, training_id, cancellation_data)

    def add_student_to_training(
        self,
        training_id: int,
        student_data: RealTrainingStudentCreate,
    ) -> RealTrainingStudent:
        """
        Добавляет студента на тренировку с полной проверкой бизнес-логики.
        """
        with transactional(self.db) as session:
            return self._add_student_to_training_logic(session, training_id, student_data)

    def update_student_attendance(
        self,
        training_id: int,
        student_id: int,
        update_data: RealTrainingStudentUpdate,
        marker_id: int,
    ) -> RealTrainingStudent:
        """
        Обновляет статус посещения и применяет бизнес-логику
        (списание занятий, штрафы).
        """
        with transactional(self.db) as session:
            return self._update_student_attendance_logic(session, training_id, student_id, update_data, marker_id)

    # --- Private Logic Methods (Non-Transactional) ---

    def _get_training(self, session: Session, training_id: int) -> Optional[RealTraining]:
        """Получение тренировки по ID"""
        return crud.get_real_training(session, training_id)

    def _get_student_training(
        self,
        session: Session,
        training_id: int,
        student_id: int
    ) -> Optional[RealTrainingStudent]:
        """Получение записи студента на тренировку"""
        return crud.get_real_training_student(session, training_id, student_id)

    def _check_cancellation_time(
        self,
        training: RealTraining,
        notification_time: datetime
    ) -> bool:
        """
        Проверяет, можно ли отменить тренировку в указанное время
        """
        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
        
        if notification_time.tzinfo is None:
            notification_time = notification_time.replace(tzinfo=timezone.utc)
        
        time_diff = (training_datetime - notification_time).total_seconds() / 3600
        
        return time_diff >= SAFE_CANCELLATION_HOURS

    def _cancel_student_logic(
        self,
        session: Session,
        training_id: int,
        student_id: int,
        cancellation_data: StudentCancellationRequest
    ) -> None:
        training = self._get_training(session, training_id)
        if not training:
            raise TrainingNotFound("Training not found")

        student_training = self._get_student_training(session, training_id, student_id)
        if not student_training:
            raise StudentNotOnTraining("Студент не найден на этой тренировке")

        can_cancel_safely = self._check_cancellation_time(
            training, 
            cancellation_data.notification_time or datetime.now(timezone.utc)
        )

        if can_cancel_safely:
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            student_training.cancellation_reason = cancellation_data.reason
            session.add(student_training)
            
            self._process_safe_cancellation_refunds(session, training, student_training)
        else:
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            student_training.cancellation_reason = cancellation_data.reason
            session.add(student_training)
            
            self._apply_cancellation_penalty(session, training, student_id)

    def _cancel_training_logic(
        self,
        session: Session,
        training_id: int,
        cancellation_data: TrainingCancellationRequest
    ) -> RealTraining:
        training = self._get_training(session, training_id)
        if not training:
            raise TrainingNotFound("Training not found")

        training.cancelled_at = datetime.now(timezone.utc)
        training.cancellation_reason = cancellation_data.reason
        session.add(training)

        student_trainings = (
            session.query(RealTrainingStudent)
            .filter(RealTrainingStudent.real_training_id == training_id)
            .all()
        )

        for student_training in student_trainings:
                self._process_training_cancellation_refunds(session, training, student_training)

        return training

    def _process_training_cancellation_refunds(
        self, 
        session: Session,
        training: RealTraining, 
        student_training: RealTrainingStudent
    ) -> None:
        student_id = student_training.student_id
        
        was_processed = training.processed_at is not None
        
        active_subscription = session.query(StudentSubscription).filter(
            and_(
                StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
                StudentSubscription.start_date <= training.training_date,
                StudentSubscription.end_date >= training.training_date,
            )
        ).first()

        if active_subscription and was_processed:
            active_subscription.sessions_left += 1
            logger.info(f"Training cancellation: Session returned to subscription for student {student_id}. "
                       f"Sessions left: {active_subscription.sessions_left} (was processed)")
        elif active_subscription and not was_processed:
            logger.info(f"Training cancellation: Session not returned for student {student_id} "
                       f"(not yet processed, sessions left: {active_subscription.sessions_left})")
        
        invoice = session.query(Invoice).filter(
            and_(
                Invoice.student_id == student_id,
                Invoice.training_id == training.id,
                Invoice.status != InvoiceStatus.CANCELLED
            )
        ).first()

        if invoice:
            try:
                # Delegate to InvoiceService for cancellation
                self.financial_service.cancel_invoice(session, invoice.id, training.cancelled_by_id or 1)
                logger.info(f"Training cancellation: Invoice {invoice.id} cancelled.")
            except Exception as e:
                logger.error(f"Error cancelling invoice {invoice.id}: {e}")
        else:
            logger.info(f"Training cancellation: No invoice found for student {student_id} on training {training.id}")

    def _process_safe_cancellation_refunds(
        self,
        session: Session,
        training: RealTraining,
        student_training: RealTrainingStudent
    ) -> None:
        student_id = student_training.student_id
        training_id = student_training.real_training_id

        was_processed = training.processed_at is not None
        
        active_subscription = session.query(StudentSubscription).filter(
            and_(
                StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
                StudentSubscription.start_date <= training.training_date,
                StudentSubscription.end_date >= training.training_date,
            )
        ).first()

        if active_subscription and was_processed:
            active_subscription.sessions_left += 1
            logger.info(f"Safe cancellation: Session returned to subscription for student {student_id} on training {training_id}. "
                       f"Sessions left: {active_subscription.sessions_left} (was processed)")
        elif active_subscription and not was_processed:
            logger.info(f"Safe cancellation: Session not returned for student {student_id} on training {training_id} "
                       f"(not yet processed, sessions left: {active_subscription.sessions_left})")

        invoice = session.query(Invoice).filter(
            and_(
                Invoice.student_id == student_id,
                Invoice.training_id == training_id,
                Invoice.status != InvoiceStatus.CANCELLED
            )
        ).first()

        if invoice:
            try:
                # Delegate to InvoiceService for cancellation
                self.financial_service.cancel_invoice(session, invoice.id, student_training.cancelled_by_id or 1)
                logger.info(f"Safe cancellation: Invoice {invoice.id} cancelled.")
            except Exception as e:
                logger.error(f"Error cancelling invoice {invoice.id}: {e}")
        else:
            logger.info(f"Safe cancellation: No invoice found for student {student_id} on training {training_id}")

    def _add_student_to_training_logic(
        self,
        session: Session,
        training_id: int,
        student_data: RealTrainingStudentCreate,
    ) -> RealTrainingStudent:
        student = student_crud.get_student_by_id(session, student_data.student_id)
        if not student:
            raise StudentInactive("Студент не найден.")
        if not student.is_active:
            raise StudentInactive("Студент неактивен.")

        existing_record = crud.get_real_training_student(session, training_id, student.id)
        if existing_record:
            raise StudentAlreadyRegistered("Студент уже записан на эту тренировку.")

        training = crud.get_real_training(session, training_id)
        if not training:
            raise TrainingNotFound("Тренировка не найдена.")

        if training.training_type.is_subscription_only:
            active_subscription = self.subscription_service.get_active_subscription(session, student.id) # Use service method

            if not active_subscription:
                raise SubscriptionRequired("Для этой тренировки требуется активный абонемент, который у студента отсутствует.")
            
            if active_subscription.sessions_left <= 0 and not active_subscription.is_auto_renew:
                raise InsufficientSessions("На абонементе закончились занятия и не включено автопродление.")

        return crud.add_student_to_training_db(session, training_id, student_data)

    def _update_student_attendance_logic(
        self,
        session: Session,
        training_id: int,
        student_id: int,
        update_data: RealTrainingStudentUpdate,
        marker_id: int,
    ) -> RealTrainingStudent:
        db_student = crud.get_real_training_student(session, training_id, student_id)
        if not db_student:
            raise StudentNotOnTraining("Студент не найден на этой тренировке")

        db_training = crud.get_real_training(session, training_id)
        if not db_training:
            raise TrainingNotFound("Тренировка не найдена")

        update_dict = update_data.model_dump(exclude_unset=True)
        
        if "status" in update_dict:
            status = update_dict["status"]
            if status == AttendanceStatus.CANCELLED:
                reason = self._handle_cancellation(session, db_training, student_id, update_data)
                update_dict["cancellation_reason"] = reason

        return crud.update_student_attendance_db(
            session, db_student, update_dict, marker_id
        )

    def _handle_cancellation(
        self,
        session: Session,
        db_training: RealTraining,
        student_id: int,
        update_data: RealTrainingStudentUpdate,
    ) -> str:
        training_datetime = datetime.combine(db_training.training_date, db_training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
        
        current_time = datetime.now(timezone.utc)
        hours_before = (training_datetime - current_time).total_seconds() / 3600
        
        student_training = self._get_student_training(session, db_training.id, student_id)
        if not student_training:
            raise StudentNotOnTraining("Студент не найден в тренировке")
        
        if hours_before >= SAFE_CANCELLATION_HOURS:
            logger.info(f"Safe cancellation for student {student_id}. No penalty - session will be deducted later.")
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            return update_data.cancellation_reason or "Своевременная отмена"
        
        else:
            logger.warning(f"Unsafe cancellation for student {student_id}. Applying penalty.")
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            
            self._apply_cancellation_penalty(session, db_training, student_id)
            return update_data.cancellation_reason or "Поздняя отмена"

    def _apply_cancellation_penalty(self, session: Session, training: RealTraining, student_id: int) -> None:
        active_subscription = session.query(StudentSubscription).filter(
            and_(
            StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
            StudentSubscription.start_date <= training.training_date,
            StudentSubscription.end_date >= training.training_date,
                StudentSubscription.sessions_left > 0
            )
        ).first()

        if active_subscription:
            active_subscription.sessions_left -= 1
            logger.info(f"Late cancellation penalty: Session deducted from subscription for student {student_id}. "
                       f"Sessions left: {active_subscription.sessions_left}")
        else:
            student = student_crud.get_student_by_id(session, student_id)
            if student:
                penalty_amount = training.training_type.price if training.training_type.price is not None else 100.0
                
                # Delegate to InvoiceService for penalty invoice creation
                invoice_data = InvoiceCreate(
                    student_id=student_id,
                    client_id=student.client_id,
                    amount=penalty_amount,
                    type=InvoiceType.LATE_CANCELLATION_FEE,
                    description=f"Штраф: поздняя отмена {training.training_type.name} {training.training_date}"
                )
                self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
                logger.info(f"Late cancellation penalty: Invoice created for student {student_id}.")