import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.crud import real_training as crud
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
from app.utils.financial_processor import cancel_invoice

logger = logging.getLogger(__name__)

# Константы для логики отмен
SAFE_CANCELLATION_HOURS = 12  # Часов до тренировки для безопасной отмены

class RealTrainingService:
    def __init__(self, db: Session):
        self.db = db

    def get_training(self, training_id: int) -> Optional[RealTraining]:
        """Получение тренировки по ID"""
        return crud.get_real_training(self.db, training_id)

    def get_student_training(
        self,
        training_id: int,
        student_id: int
    ) -> Optional[RealTrainingStudent]:
        """Получение записи студента на тренировку"""
        return crud.get_real_training_student(self.db, training_id, student_id)

    def check_cancellation_time(
        self,
        training: RealTraining,
        notification_time: datetime
    ) -> bool:
        """
        Проверяет, можно ли отменить тренировку в указанное время
        
        Args:
            training: Тренировка
            notification_time: Время уведомления об отмене
            
        Returns:
            True если отмена возможна, False если нет
        """
        # Создаем datetime для тренировки
        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
        
        # Приводим notification_time к UTC если нужно
        if notification_time.tzinfo is None:
            notification_time = notification_time.replace(tzinfo=timezone.utc)
        
        # Вычисляем разницу в часах
        time_diff = (training_datetime - notification_time).total_seconds() / 3600
        
        return time_diff >= SAFE_CANCELLATION_HOURS

    async def cancel_student(
        self,
        training_id: int,
        student_id: int,
        cancellation_data: StudentCancellationRequest
    ) -> None:
        """
        Отмена участия студента в тренировке
        """
        # Получаем тренировку и студента
        training = self.get_training(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        student_training = self.get_student_training(training_id, student_id)
        if not student_training:
            raise HTTPException(status_code=404, detail="Student not found on this training")

        # Проверяем время отмены
        can_cancel_safely = self.check_cancellation_time(
            training, 
            cancellation_data.cancellation_time or datetime.now(timezone.utc)
        )

        if can_cancel_safely:
            # Безопасная отмена
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            student_training.cancellation_reason = cancellation_data.reason
            self.db.add(student_training)
            
            # Обрабатываем возвраты при безопасной отмене
            await self._process_safe_cancellation_refunds(training, student_training)
        else:
            # Небезопасная отмена - применяем штрафы
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            student_training.cancellation_reason = cancellation_data.reason
            self.db.add(student_training)
            
            # Применяем штрафы
            self._apply_cancellation_penalty(training, student_id)

        self.db.commit()

    async def cancel_training(
        self,
        training_id: int,
        cancellation_data: TrainingCancellationRequest
    ) -> RealTraining:
        """
        Отмена всей тренировки
        """
        # Получаем тренировку
        training = self.get_training(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        # Отменяем тренировку
        training.cancelled_at = datetime.now(timezone.utc)
        training.cancellation_reason = cancellation_data.reason
        self.db.add(training)

        # Получаем всех студентов на тренировке
        student_trainings = (
            self.db.query(RealTrainingStudent)
            .filter(RealTrainingStudent.real_training_id == training_id)
            .all()
        )

        # Обрабатываем каждого студента
        for student_training in student_trainings:
                await self._process_training_cancellation_refunds(training, student_training)

        self.db.commit()
        return training

    async def _process_training_cancellation_refunds(
        self, 
        training: RealTraining, 
        student_training: RealTrainingStudent
    ) -> None:
        """
        Обрабатывает возвраты при отмене тренировки:
        - Возвращает занятие в абонемент если тренировка уже была обработана
        - Отменяет инвойс и возвращает средства если есть
        """
        student_id = student_training.student_id
        
        # Проверяем, была ли тренировка уже обработана (процессинг)
        was_processed = training.processed_at is not None
        
        # Ищем активный абонемент
        active_subscription = self.db.query(StudentSubscription).filter(
            and_(
                StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
                StudentSubscription.start_date <= training.training_date,
                StudentSubscription.end_date >= training.training_date,
            )
        ).first()

        if active_subscription and was_processed:
            # Занятие уже было списано - возвращаем его
            active_subscription.sessions_left += 1
            logger.info(f"Training cancellation: Session returned to subscription for student {student_id}. "
                       f"Sessions left: {active_subscription.sessions_left} (was processed)")
        elif active_subscription and not was_processed:
            # Занятие еще не списано - ничего не возвращаем
            logger.info(f"Training cancellation: Session not returned for student {student_id} "
                       f"(not yet processed, sessions left: {active_subscription.sessions_left})")
        
        # Ищем и отменяем инвойс, если он существует
        invoice = self.db.query(Invoice).filter(
            and_(
                Invoice.student_id == student_id,
                Invoice.training_id == training.id,
                Invoice.status != InvoiceStatus.CANCELLED
            )
        ).first()

        if invoice:
            # Отменяем инвойс через FinancialProcessor
            try:
                cancelled_invoice = cancel_invoice(
                    self.db,
                    invoice.id,
                    training.cancelled_by_id or 1  # Используем ID администратора
                )
            
            # Возвращаем средства на баланс клиента
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if student and student.client:
                student.client.balance += invoice.amount
                logger.info(f"Training cancellation: Invoice {invoice.id} cancelled and "
                           f"{invoice.amount}р returned to client {student.client.id} balance")
            except Exception as e:
                logger.error(f"Error cancelling invoice {invoice.id}: {e}")
        else:
            logger.info(f"Training cancellation: No invoice found for student {student_id} on training {training.id}")

    async def _process_safe_cancellation_refunds(
        self,
        training: RealTraining,
        student_training: RealTrainingStudent
    ) -> None:
        """
        Обрабатывает возвраты при безопасной отмене:
        - Возвращает занятие в абонемент если тренировка уже была обработана
        - Отменяет инвойс и возвращает средства если есть
        """
        student_id = student_training.student_id
        training_id = student_training.real_training_id

        # Проверяем, была ли тренировка уже обработана (процессинг)
        was_processed = training.processed_at is not None
        
        # Ищем активный абонемент
        active_subscription = self.db.query(StudentSubscription).filter(
            and_(
                StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
                StudentSubscription.start_date <= training.training_date,
                StudentSubscription.end_date >= training.training_date,
            )
        ).first()

        if active_subscription and was_processed:
            # Занятие уже было списано - возвращаем его
            active_subscription.sessions_left += 1
            logger.info(f"Safe cancellation: Session returned to subscription for student {student_id} on training {training_id}. "
                       f"Sessions left: {active_subscription.sessions_left} (was processed)")
        elif active_subscription and not was_processed:
            # Занятие еще не списано - ничего не возвращаем
            logger.info(f"Safe cancellation: Session not returned for student {student_id} on training {training_id} "
                       f"(not yet processed, sessions left: {active_subscription.sessions_left})")

        # Отменяем инвойс, если он существует и не отменен
        invoice = self.db.query(Invoice).filter(
            and_(
                Invoice.student_id == student_id,
                Invoice.training_id == training_id,
                Invoice.status != InvoiceStatus.CANCELLED
            )
        ).first()

        if invoice:
            # Отменяем инвойс через FinancialProcessor
            try:
                cancelled_invoice = cancel_invoice(
                    self.db,
                    invoice.id,
                    student_training.cancelled_by_id or 1  # Используем ID администратора
                )
            
            # Возвращаем средства на баланс клиента
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if student and student.client:
                student.client.balance += invoice.amount
                logger.info(f"Safe cancellation: Invoice {invoice.id} cancelled and "
                           f"{invoice.amount}р returned to client {student.client.id} balance")
            except Exception as e:
                logger.error(f"Error cancelling invoice {invoice.id}: {e}")
        else:
            logger.info(f"Safe cancellation: No invoice found for student {student_id} on training {training_id}")

    def add_student_to_training(
        self,
        training_id: int,
        student_data: RealTrainingStudentCreate,
    ) -> RealTrainingStudent:
        """
        Добавляет студента на тренировку с полной проверкой бизнес-логики.
        """
        # 1. Проверяем активность студента
        student = self.db.query(Student).filter(Student.id == student_data.student_id).first()
        if not student or not student.is_active:
            raise HTTPException(status_code=400, detail="Студент не найден или неактивен.")

        # 2. Проверяем, не записан ли студент уже на эту тренировку
        existing_record = self.db.query(RealTrainingStudent).filter(
            RealTrainingStudent.real_training_id == training_id,
            RealTrainingStudent.student_id == student.id,
        ).first()
        if existing_record:
            raise HTTPException(status_code=409, detail="Студент уже записан на эту тренировку.")

        # 3. Загружаем тренировку и её тип
        training = self.db.query(RealTraining).options(
            joinedload(RealTraining.training_type)
        ).filter(RealTraining.id == training_id).first()
        if not training:
            raise HTTPException(status_code=404, detail="Тренировка не найдена.")

        # 4. Проверяем необходимость абонемента
        if training.training_type.is_subscription_only:
            active_subscription = self.db.query(StudentSubscription).filter(
                StudentSubscription.student_id == student.id,
                StudentSubscription.status == "active",
                StudentSubscription.start_date <= training.training_date,
                StudentSubscription.end_date >= training.training_date,
            ).first()

            if not active_subscription:
                raise HTTPException(status_code=400, detail="Для этой тренировки требуется активный абонемент, который у студента отсутствует.")
            
            if active_subscription.sessions_left <= 0 and not active_subscription.is_auto_renew:
                raise HTTPException(status_code=400, detail="На абонементе закончились занятия и не включено автопродление.")

        # Логика добавления вынесена в CRUD
        return crud.add_student_to_training_db(self.db, training_id, student_data)

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
        db_student = crud.get_real_training_student(self.db, training_id, student_id)
        if not db_student:
            raise HTTPException(status_code=404, detail="Студент не найден на этой тренировке")

        db_training = crud.get_real_training(self.db, training_id)
        if not db_training:
            raise HTTPException(status_code=404, detail="Тренировка не найдена")

        update_dict = update_data.model_dump(exclude_unset=True)
        
        if "status" in update_dict:
            status = update_dict["status"]
            # Если отмена, применяем логику "умных штрафов"
            if status == AttendanceStatus.CANCELLED:
                reason = self._handle_cancellation(db_training, student_id, update_data)
                update_dict["cancellation_reason"] = reason

        return crud.update_student_attendance_db(
            self.db, db_student, update_dict, marker_id
        )

    def _handle_cancellation(
        self,
        db_training: RealTraining,
        student_id: int,
        update_data: RealTrainingStudentUpdate,
    ) -> str:
        # Создаем timezone-aware datetime для тренировки
        training_datetime = datetime.combine(db_training.training_date, db_training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
        
        # Используем текущее время в UTC
        current_time = datetime.now(timezone.utc)
        hours_before = (training_datetime - current_time).total_seconds() / 3600
        
        # Получаем запись студента
        student_training = self.get_student_training(db_training.id, student_id)
        if not student_training:
            raise HTTPException(status_code=404, detail="Студент не найден в тренировке")
        
        # Безопасная отмена (>12 часов) - НЕ списываем занятие
        if hours_before >= SAFE_CANCELLATION_HOURS:
            logger.info(f"Safe cancellation for student {student_id}. No penalty - session will be deducted later.")
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            return update_data.cancellation_reason or "Своевременная отмена"
        
        # Небезопасная отмена (<12 часов) - СРАЗУ списываем занятие как штраф
        else:
            logger.warning(f"Unsafe cancellation for student {student_id}. Applying penalty.")
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            
            # Применяем штрафы
            self._apply_cancellation_penalty(db_training, student_id)
            return update_data.cancellation_reason or "Поздняя отмена"

    def _apply_cancellation_penalty(self, training: RealTraining, student_id: int) -> None:
        """
        Применяет штрафы за позднюю отмену:
        - Списывает занятие с абонемента если есть активный
        - Создает штрафной инвойс если нет абонемента
        """
        # Ищем активный абонемент
        active_subscription = self.db.query(StudentSubscription).filter(
            and_(
            StudentSubscription.student_id == student_id,
                StudentSubscription.status == "active",
            StudentSubscription.start_date <= training.training_date,
            StudentSubscription.end_date >= training.training_date,
                StudentSubscription.sessions_left > 0
            )
        ).first()

        if active_subscription:
            # Списываем занятие с абонемента
            active_subscription.sessions_left -= 1
            logger.info(f"Late cancellation penalty: Session deducted from subscription for student {student_id}. "
                       f"Sessions left: {active_subscription.sessions_left}")
        else:
            # Создаем штрафной инвойс если нет абонемента
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if student:
                # Получаем цену тренировки или устанавливаем значение по умолчанию
                penalty_amount = training.training_type.price if training.training_type.price is not None else 100.0
                
                invoice = Invoice(
                    student_id=student_id,
                    client_id=student.client_id,
                    amount=penalty_amount,
                    type=InvoiceType.LATE_CANCELLATION_FEE,
                    description=f"Штраф: поздняя отмена {training.training_type.name} {training.training_date}"
                )
                self.db.add(invoice)
                logger.info(f"Late cancellation penalty: Invoice created for student {student_id}.") 