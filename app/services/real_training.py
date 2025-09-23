import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.crud import real_training as crud
from app.crud import student as student_crud
from app.crud import invoice as invoice_crud
from app.models import (
    RealTraining,
    RealTrainingStudent,
    StudentSubscription,
    Invoice,
    InvoiceStatus,
    InvoiceType
)
from app.models.real_training import AttendanceStatus
from app.schemas.real_training import (
    RealTrainingStudentCreate,
    RealTrainingStudentUpdate,
    StudentCancellationRequest,
    TrainingCancellationRequest,
    RealTrainingWithTrialStudentCreate,
)

from app.database import transactional
from app.services.financial import FinancialService
from app.services.subscription import SubscriptionService
from app.services.trainer_salary import TrainerSalaryService
from app.errors.real_training_errors import (
    TrainingNotFound,
    StudentNotOnTraining,
    StudentAlreadyRegistered,
    StudentInactive,
    SubscriptionRequired,
    InsufficientSessions
)
from app.schemas.invoice import InvoiceCreate
import enum as _enum

logger = logging.getLogger(__name__)

# Константы для логики отмен
SAFE_CANCELLATION_HOURS = 12  # Фолбэк: часов до тренировки для безопасной отмены

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

    def create_real_training_with_trial_student(
        self,
        training_data: RealTrainingWithTrialStudentCreate,
    ) -> RealTraining:
        """
        Создает новую тренировку с одним пробным студентом.
        """
        with transactional(self.db) as session:
            # Create the real training
            db_training = crud.create_real_training(session, training_data)

            # Add the trial student
            student_data = RealTrainingStudentCreate(
                student_id=training_data.student_id,
                is_trial=True
            )
            self._add_student_to_training_logic(session, db_training.id, student_data)

            return db_training

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
        # Normalize datetimes
        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)

        if notification_time.tzinfo is None:
            notification_time = notification_time.replace(tzinfo=timezone.utc)

        # If training type defines cancellation policy - use it
        tt = getattr(training, 'training_type', None)
        # Fallback: compute hours difference
        time_diff_hours = (training_datetime - notification_time).total_seconds() / 3600

        if not tt:
            return time_diff_hours >= SAFE_CANCELLATION_HOURS

        mode = getattr(tt, 'cancellation_mode', None) or 'FLEXIBLE'
        # Normalize SQLA Enum to raw value if needed
        if isinstance(mode, _enum.Enum):
            mode = mode.value
        if mode == 'FLEXIBLE':
            safe_hours = getattr(tt, 'safe_cancel_hours', None)
            if safe_hours is None:
                safe_hours = SAFE_CANCELLATION_HOURS
            return time_diff_hours >= safe_hours

        # FIXED mode: evaluate by comparing notification_time to configured safe time (morning/evening)
        # Determine whether the training is considered morning or evening (12:00 threshold)
        start_hour = training.start_time.hour
        is_morning = start_hour < 12

        if is_morning:
            safe_time = getattr(tt, 'safe_cancel_time_morning', None)
            prev_day = getattr(tt, 'safe_cancel_time_morning_prev_day', False)
        else:
            safe_time = getattr(tt, 'safe_cancel_time_evening', None)
            prev_day = getattr(tt, 'safe_cancel_time_evening_prev_day', False)

        if safe_time is None:
            # If not configured, fall back to flexible hours
            safe_hours = getattr(tt, 'safe_cancel_hours', None) or SAFE_CANCELLATION_HOURS
            return time_diff_hours >= safe_hours

        # Build the safe cancellation datetime
        safe_date = training.training_date
        if prev_day:
            safe_date = safe_date - timedelta(days=1)

        safe_datetime = datetime.combine(safe_date, safe_time)
        if safe_datetime.tzinfo is None:
            safe_datetime = safe_datetime.replace(tzinfo=timezone.utc)

        return notification_time <= safe_datetime

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
            student_training.cancelled_at = datetime.now(timezone.utc)
            session.add(student_training)
            
            # Process refunds/returns atomically per student
            try:
                self._process_safe_cancellation_refunds(session, training, student_training)
            except Exception as e:
                logger.exception(f"Error while processing safe cancellation refunds for student {student_id}: {e}")
                raise
        else:
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            student_training.cancellation_reason = cancellation_data.reason
            student_training.cancelled_at = datetime.now(timezone.utc)
            session.add(student_training)
            
            try:
                self._apply_cancellation_penalty(session, training, student_id)
            except Exception as e:
                logger.exception(f"Error while applying cancellation penalty for student {student_id}: {e}")
                raise

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

        # If training was already processed (sessions were deducted), return session if it was deducted
        if active_subscription:
            # If session_deducted is True - that means session was already taken and should be returned
            if getattr(student_training, 'session_deducted', False):
                active_subscription.sessions_left += 1
                student_training.session_deducted = False
                logger.info(f"Training cancellation: Session returned to subscription for student {student_id}. "
                           f"Sessions left: {active_subscription.sessions_left} (returned)")
            else:
                logger.info(f"Training cancellation: Session was not deducted for student {student_id} - nothing to return.")
        
        invoice = session.query(Invoice).filter(
            and_(
                Invoice.student_id == student_id,
                Invoice.training_id == training.id,
                Invoice.status != InvoiceStatus.CANCELLED
            )
        ).first()

        if invoice:
            try:
                # SAFE training cancellation: if invoice was PAID -> refund, else just cancel
                if invoice.status == InvoiceStatus.PAID:
                    self.financial_service._refund_paid_invoice(session, invoice, cancelled_by_id=getattr(training, 'cancelled_by_id', 1))
                else:
                    invoice_crud.cancel_invoice(session, invoice.id, cancelled_by_id=getattr(training, 'cancelled_by_id', 1))
                logger.info(f"Training cancellation: Invoice {invoice.id} handled (status: {invoice.status}).")
            except Exception as e:
                logger.exception(f"Error cancelling/refunding invoice {invoice.id}: {e}")
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

        # Subscription user
        if student_training.subscription_id:
            active_subscription = session.query(StudentSubscription).filter(
                StudentSubscription.id == student_training.subscription_id
            ).first()

            if active_subscription:
                if student_training.session_deducted:
                    # If a session was deducted, it means it was counted against the subscription.
                    # Now, instead of returning it to sessions_left, add to skipped_sessions (max 3).
                    if active_subscription.skipped_sessions < 3:
                        active_subscription.skipped_sessions += 1
                        logger.info(f"Safe cancellation: Session added to skipped_sessions for student {student_id} on training {training_id}. "
                                   f"Skipped sessions: {active_subscription.skipped_sessions}")
                    else:
                        logger.info(f"Safe cancellation: Skipped sessions limit reached for student {student_id}. Session not added.")
                    
                    # IMPORTANT: session_deducted remains True because the session is accounted for as a skipped session.
                    # It is not returned to sessions_left, but it is also not available for future deductions.
                else:
                    logger.info(f"Safe cancellation: No session deduction was recorded for student {student_id} on training {training_id}")

        # Pay-per-session user
        else:
            invoice = session.query(Invoice).filter(
                and_(
                    Invoice.student_id == student_id,
                    Invoice.training_id == training_id,
                    Invoice.status != InvoiceStatus.CANCELLED
                )
            ).first()

            if invoice:
                try:
                    if invoice.status == InvoiceStatus.PAID:
                        self.financial_service._refund_paid_invoice(session, invoice, cancelled_by_id=student_training.attendance_marked_by_id or 1)
                    else:
                        invoice_crud.cancel_invoice(session, invoice.id, cancelled_by_id=student_training.attendance_marked_by_id or 1)
                    logger.info(f"Safe cancellation: Invoice {invoice.id} handled (status: {invoice.status}).")
                except Exception as e:
                    logger.exception(f"Error cancelling/refunding invoice {invoice.id}: {e}")
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
        
        if student_data.is_trial:
            student_data.requires_payment = False
            # Check if student already had a trial training
            had_trial = session.query(RealTrainingStudent).filter(
                RealTrainingStudent.student_id == student.id,
                RealTrainingStudent.is_trial == True
            ).first()
            if had_trial:
                raise ValueError("У студента уже была пробная тренировка.")

            # Check if student had any paid trainings
            had_paid_training = session.query(RealTrainingStudent).filter(
                RealTrainingStudent.student_id == student.id,
                RealTrainingStudent.requires_payment == True,
                RealTrainingStudent.status != AttendanceStatus.CANCELLED_SAFE
            ).first()
            if had_paid_training:
                raise ValueError("Студент уже посещал платные тренировки.")

        # Check capacity limits
        if training.training_type.max_participants:
            current_active_students = session.query(RealTrainingStudent).filter(
                RealTrainingStudent.real_training_id == training_id,
                ~RealTrainingStudent.status.in_([AttendanceStatus.CANCELLED_SAFE, AttendanceStatus.CANCELLED_PENALTY])
            ).count()
            
            if current_active_students >= training.training_type.max_participants:
                raise ValueError(f"Тренировка заполнена. Максимальное количество участников: {training.training_type.max_participants}")

        if training.training_type.is_subscription_only and not student_data.is_trial:
            active_subscription = self.subscription_service.get_active_subscription(session, student.id) # Use service method

            if not active_subscription:
                raise SubscriptionRequired("Для этой тренировки требуется активный абонемент, который у студента отсутствует.")
            
            if active_subscription.sessions_left <= 0 and not active_subscription.is_auto_renew:
                raise InsufficientSessions("На абонементе закончились занятия и не включено автопродление.")

        requires_payment = not student_data.is_trial

        return crud.add_student_to_training_db(session, training_id, student_data, is_trial=student_data.is_trial, requires_payment=requires_payment)

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
            # status may come as a plain string from the API (e.g. "CANCELLED")
            # or as a specific cancellation variant like "CANCELLED_SAFE" / "CANCELLED_PENALTY".
            # AttendanceStatus enum doesn't have a generic CANCELLED member, so detect by value.
            status_value = status.value if hasattr(status, "value") else status
            if isinstance(status_value, str) and status_value in ("CANCELLED", AttendanceStatus.CANCELLED_SAFE.value, AttendanceStatus.CANCELLED_PENALTY.value):
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
        # Determine whether cancellation is safe according to training type rules
        current_time = datetime.now(timezone.utc)

        student_training = self._get_student_training(session, db_training.id, student_id)
        if not student_training:
            raise StudentNotOnTraining("Студент не найден в тренировке")

        can_cancel_safely = self._check_cancellation_time(db_training, current_time)

        if can_cancel_safely:
            logger.info(f"Safe cancellation for student {student_id}. No penalty - session will be deducted later.")
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            return update_data.cancellation_reason or "Своевременная отмена"
        else:
            logger.warning(f"Unsafe cancellation for student {student_id}. Applying penalty.")
            student_training.status = AttendanceStatus.CANCELLED_PENALTY

            self._apply_cancellation_penalty(session, db_training, student_id)
            return update_data.cancellation_reason or "Поздняя отмена"

    def _apply_cancellation_penalty(self, session: Session, training: RealTraining, student_id: int) -> None:
        student_training = self._get_student_training(session, training.id, student_id)
        if not student_training:
            # This should not happen if called from _cancel_student_logic
            logger.error(f"Student training record not found for student {student_id} in training {training.id}")
            return

        # Subscription user
        if student_training.subscription_id:
            active_subscription = session.query(StudentSubscription).filter(
                StudentSubscription.id == student_training.subscription_id
            ).first()

            if active_subscription and active_subscription.sessions_left > 0:
                if not student_training.session_deducted:
                    active_subscription.sessions_left -= 1
                    student_training.session_deducted = True
                    logger.info(f"Late cancellation penalty: Session deducted from subscription for student {student_id}. "
                               f"Sessions left: {active_subscription.sessions_left}")
                else:
                    logger.info(f"Late cancellation penalty: Session already deducted for student {student_id}.")
            else:
                # Fallback to invoice if subscription has no sessions left
                self._handle_pay_per_session_penalty(session, training, student_id)
        # Pay-per-session user
        else:
            self._handle_pay_per_session_penalty(session, training, student_id)

    def _handle_pay_per_session_penalty(self, session: Session, training: RealTraining, student_id: int) -> None:
        invoice = session.query(Invoice).filter(
            Invoice.student_id == student_id,
            Invoice.training_id == training.id,
            Invoice.status == InvoiceStatus.PENDING
        ).first()

        if invoice:
            # If a PENDING invoice exists, mark it as UNPAID and attempt to pay
            invoice.status = InvoiceStatus.UNPAID
            session.add(invoice)
            session.flush()
            logger.info(f"Late cancellation penalty: Invoice {invoice.id} for student {student_id} marked as UNPAID.")
            self.financial_service.attempt_auto_payment(session, invoice.id)
        else:
            # If no PENDING invoice exists, create a new UNPAID invoice and attempt to pay
            student = student_crud.get_student_by_id(session, student_id)
            if student:
                penalty_amount = training.training_type.price if training.training_type and training.training_type.price is not None else 100.0
                invoice_data = InvoiceCreate(
                    student_id=student_id,
                    client_id=student.client_id,
                    amount=penalty_amount,
                    training_id=training.id,
                    type=InvoiceType.TRAINING,
                    description=f"Поздняя отмена {training.training_type.name} {training.training_date}",
                    status=InvoiceStatus.UNPAID
                )
                new_invoice = self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
                logger.info(f"Late cancellation penalty: New UNPAID invoice {new_invoice.id} created for student {student_id}.")