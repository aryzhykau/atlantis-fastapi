from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from app.crud import real_training as crud
from app.models import (
    RealTraining,
    RealTrainingStudent,
    Student,
    StudentSubscription,
    Invoice,
    InvoiceType,
    InvoiceStatus,
)
from app.schemas.real_training import (
    RealTrainingCreate,
    RealTrainingUpdate,
    StudentCancellationRequest,
    TrainingCancellationRequest,
)
from app.schemas.real_training_student import (
    RealTrainingStudentCreate,
    RealTrainingStudentUpdate,
)
from app.models.real_training import SAFE_CANCELLATION_HOURS, AttendanceStatus

logger = logging.getLogger(__name__)


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
        training = crud.get_real_training(self.db, training_id)
        if not training:
            return None
        
        for student_training in training.students:
            if student_training.student_id == student_id:
                return student_training
        return None

    def check_cancellation_time(
        self,
        training: RealTraining,
        notification_time: datetime
    ) -> bool:
        """
        Проверка времени отмены тренировки
        Возвращает True если отмена возможна (более 12 часов до начала)
        """
        # Создаем timezone-aware datetime для тренировки
        training_datetime = datetime.combine(training.training_date, training.start_time)
        if training_datetime.tzinfo is None:
            training_datetime = training_datetime.replace(tzinfo=timezone.utc)
        
        # Убеждаемся что notification_time тоже timezone-aware
        if notification_time.tzinfo is None:
            notification_time = notification_time.replace(tzinfo=timezone.utc)
        
        hours_before = (training_datetime - notification_time).total_seconds() / 3600
        return hours_before >= SAFE_CANCELLATION_HOURS

    async def cancel_student(
        self,
        training_id: int,
        student_id: int,
        cancellation_data: StudentCancellationRequest
    ) -> None:
        """
        Отмена участия студента в реальной тренировке:
        1. Проверка времени до начала (12 часов)
        2. Если отмена безопасная (>12ч) - устанавливаем статус CANCELLED_SAFE
        3. Если отмена небезопасная (<12ч) - устанавливаем статус CANCELLED_PENALTY + штрафы
        4. Студент остается в тренировке с соответствующим статусом
        """
        # Получаем тренировку
        training = self.get_training(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        # Получаем запись студента
        student_training = self.get_student_training(training_id, student_id)
        if not student_training:
            raise HTTPException(status_code=404, detail="Студент не найден в тренировке")

        # Проверяем время до начала
        is_safe_cancellation = self.check_cancellation_time(training, cancellation_data.notification_time)

        if is_safe_cancellation:
            # Безопасная отмена - устанавливаем статус без штрафа
            student_training.status = AttendanceStatus.CANCELLED_SAFE
            logger.info(f"Safe cancellation for student {student_id} on training {training_id}")
            
            # При безопасной отмене также обрабатываем финансовые возвраты
            await self._process_safe_cancellation_refunds(training, student_training)
        else:
            # Небезопасная отмена - устанавливаем статус со штрафом
            student_training.status = AttendanceStatus.CANCELLED_PENALTY
            logger.warning(f"Unsafe cancellation for student {student_id} on training {training_id}")
            
            # Применяем штрафы
            self._apply_cancellation_penalty(training, student_id)

        # Сохраняем информацию об отмене
        student_training.notification_time = cancellation_data.notification_time
        student_training.cancelled_at = datetime.now(timezone.utc)
        student_training.cancellation_reason = cancellation_data.reason

        # Сохраняем изменения (НЕ удаляем студента!)
        self.db.commit()

    async def cancel_training(
        self,
        training_id: int,
        cancellation_data: TrainingCancellationRequest
    ) -> RealTraining:
        """
        Полная отмена тренировки с обработкой всех студентов
        1. Проверка тренировки
        2. Возврат тренировок студентам
        3. Запуск финансовых процессов
        4. Закрытие тренировки
        """
        # Получаем тренировку
        training = self.get_training(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        # Проверяем что тренировка еще не отменена
        if training.cancelled_at:
            raise HTTPException(status_code=400, detail="Training is already cancelled")

        # Отмечаем тренировку как отмененную
        training.cancelled_at = datetime.now(timezone.utc)
        training.cancellation_reason = cancellation_data.reason

        # Обрабатываем каждого студента
        for student_training in training.students:
            # Отмечаем отмену для студента
            student_training.cancelled_at = datetime.now(timezone.utc)
            student_training.cancellation_reason = cancellation_data.reason

            # Если нужно запустить финансовые процессы
            if cancellation_data.process_refunds:
                await self._process_training_cancellation_refunds(training, student_training)

        self.db.commit()
        return training

    async def _process_training_cancellation_refunds(
        self, 
        training: RealTraining, 
        student_training: RealTrainingStudent
    ) -> None:
        """
        Обрабатывает финансовые возвраты при отмене тренировки:
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
                StudentSubscription.status == "active",  # Используем вычисляемое свойство
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
            # Отменяем инвойс
            invoice.status = InvoiceStatus.CANCELLED
            invoice.cancelled_at = datetime.now(timezone.utc)
            invoice.cancellation_reason = f"Отмена тренировки: {training.cancellation_reason}"
            
            # Возвращаем средства на баланс клиента
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if student and student.client:
                student.client.balance += invoice.amount
                logger.info(f"Training cancellation: Invoice {invoice.id} cancelled and "
                           f"{invoice.amount}р returned to client {student.client.id} balance")
        else:
            logger.info(f"Training cancellation: No invoice found for student {student_id} on training {training.id}")
            
        # Примечание: Занятия в абонементе не возвращаем, так как они списываются 
        # только при генерации инвойсов на завтра (вечером), а не при записи на тренировку

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
                StudentSubscription.status == "active",  # Используем вычисляемое свойство
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
            invoice.status = InvoiceStatus.CANCELLED
            invoice.cancelled_at = datetime.now(timezone.utc)
            invoice.cancellation_reason = f"Безопасная отмена участия: {student_training.cancellation_reason}"
            
            # Возвращаем средства на баланс клиента
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if student and student.client:
                student.client.balance += invoice.amount
                logger.info(f"Safe cancellation: Invoice {invoice.id} cancelled and "
                           f"{invoice.amount}р returned to client {student.client.id} balance")
        else:
            logger.info(f"Safe cancellation: No invoice found for student {student_id} on training {training_id}")
            
        # Примечание: Занятия в абонементе не возвращаем, так как они списываются 
        # только при генерации инвойсов на завтра (вечером), а не при записи на тренировку

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
                StudentSubscription.status == "active",  # Используем вычисляемое свойство
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
        Применяет штрафы за небезопасную отмену (<12 часов):
        - Списывает занятие с абонемента если есть
        - Создает штрафной инвойс если абонемента нет
        """
        active_subscription = self.db.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.status == "active",  # Используем вычисляемое свойство
            StudentSubscription.start_date <= training.training_date,
            StudentSubscription.end_date >= training.training_date,
        ).first()

        if active_subscription and active_subscription.sessions_left > 0:
            # Списываем занятие с абонемента как штраф
            active_subscription.sessions_left -= 1
            logger.info(f"Late cancellation penalty: Session deducted from subscription for student {student_id}.")
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