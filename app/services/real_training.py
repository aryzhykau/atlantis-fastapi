from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.crud import real_training as crud
from app.models import RealTraining, RealTrainingStudent, Student
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


# Константы
SAFE_CANCELLATION_HOURS = 12  # Минимальное количество часов для безопасной отмены


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
        training_datetime = datetime.combine(training.training_date, training.start_time)
        hours_before = (training_datetime - notification_time).total_seconds() / 3600
        return hours_before >= SAFE_CANCELLATION_HOURS

    async def cancel_student(
        self,
        training_id: int,
        student_id: int,
        cancellation_data: StudentCancellationRequest
    ) -> None:
        """
        Отмена участия студента с проверками:
        1. Проверка времени до начала (12 часов)
        2. Проверка лимита переносов
        3. Обработка абонемента
        """
        # Получаем тренировку
        training = self.get_training(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        # Проверяем время до начала
        if not self.check_cancellation_time(training, cancellation_data.notification_time):
            raise HTTPException(
                status_code=400,
                detail=f"Too late to cancel - must be at least {SAFE_CANCELLATION_HOURS} hours before"
            )

        # Проверяем лимит переносов
        if not self.stats_service.check_reschedule_limit(student_id, training.training_date):
            raise HTTPException(
                status_code=400,
                detail="Monthly reschedule limit exceeded (maximum 3 reschedules per month)"
            )

        # Получаем запись студента
        student_training = self.get_student_training(training_id, student_id)
        if not student_training:
            raise HTTPException(status_code=404, detail="Student not found in training")

        # Сохраняем информацию об отмене
        student_training.notification_time = cancellation_data.notification_time
        student_training.cancelled_at = datetime.now()
        student_training.cancellation_reason = cancellation_data.reason

        # Увеличиваем счетчик переносов
        self.stats_service.increment_reschedule_count(student_id, training.training_date)

        # Обрабатываем абонемент если он есть
        if student_training.subscription_id:
            # TODO: Добавить интеграцию с сервисом абонементов
            # await self.subscription_service.process_cancellation(
            #     student_training.subscription_id,
            #     is_timely_cancellation=True
            # )
            pass

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
        training.cancelled_at = datetime.utcnow()
        training.cancellation_reason = cancellation_data.reason

        # Обрабатываем каждого студента
        for student_training in training.students:
            # Отмечаем отмену для студента
            student_training.cancelled_at = datetime.utcnow()
            student_training.cancellation_reason = cancellation_data.reason

            # Если нужно запустить финансовые процессы
            if cancellation_data.process_refunds and student_training.subscription_id:
                # TODO: Добавить интеграцию с сервисом абонементов
                # await self.subscription_service.process_training_cancellation(
                #     student_training.subscription_id,
                #     training.training_date
                # )
                pass

        self.db.commit()
        return training 