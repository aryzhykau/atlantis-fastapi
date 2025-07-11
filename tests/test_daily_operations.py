from datetime import date, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import (
    RealTraining,
    RealTrainingStudent,
    Student,
    StudentSubscription,
    TrainingType,
)
from app.models.real_training import AttendanceStatus
from app.services.daily_operations import DailyOperationsService


@pytest.fixture
def today_training(
    db_session: Session, test_training_type_subscription: TrainingType
) -> RealTraining:
    training = RealTraining(
        training_date=date.today(),
        start_time=time(10, 0),
        training_type_id=test_training_type_subscription.id,
        responsible_trainer_id=1,
    )
    db_session.add(training)
    db_session.commit()
    return training


@pytest.fixture
def tomorrow_training(
    db_session: Session, test_training_type_subscription: TrainingType
) -> RealTraining:
    training = RealTraining(
        training_date=date.today() + timedelta(days=1),
        start_time=time(10, 0),
        training_type_id=test_training_type_subscription.id,
        responsible_trainer_id=1,
    )
    db_session.add(training)
    db_session.commit()
    return training


@pytest.fixture
def registered_student_for_today(
    db_session: Session, today_training: RealTraining, test_student: Student
) -> RealTrainingStudent:
    rts = RealTrainingStudent(
        real_training_id=today_training.id,
        student_id=test_student.id,
        status=AttendanceStatus.REGISTERED,
    )
    db_session.add(rts)
    db_session.commit()
    return rts


class TestDailyOperationsService:
    def test_process_today_attendance(
        self,
        db_session: Session,
        today_training: RealTraining,
        registered_student_for_today: RealTrainingStudent,
    ):
        """
        Тест: Статус студента должен измениться с REGISTERED на PRESENT
        для сегодняшней тренировки.
        """
        service = DailyOperationsService(db_session)
        service._process_today_attendance(date.today())
        db_session.commit()

        db_session.refresh(registered_student_for_today)
        assert registered_student_for_today.status == AttendanceStatus.PRESENT

    def test_process_tomorrow_finances(
        self, db_session: Session, tomorrow_training: RealTraining
    ):
        """
        Тест: Финансовая обработка для завтрашней тренировки должна быть вызвана.
        """
        service = DailyOperationsService(db_session)

        # Мокаем сервис финансовой обработки
        mock_training_processing_service = MagicMock()
        service.training_processing_service = mock_training_processing_service

        service._process_tomorrow_finances(date.today() + timedelta(days=1))

        # Проверяем, что метод обработки был вызван для нашей завтрашней тренировки
        mock_training_processing_service.process_training.assert_called_once_with(
            tomorrow_training
        )

    def test_full_daily_operations_flow(
        self,
        db_session: Session,
        today_training: RealTraining,
        tomorrow_training: RealTraining,
        registered_student_for_today: RealTrainingStudent,
    ):
        """
        Тест: Полный цикл ежедневных операций.
        Проверяем, что оба этапа (посещаемость и финансы) вызываются корректно.
        """
        service = DailyOperationsService(db_session)

        # Мокаем финансовый сервис, чтобы не выполнять реальные списания
        mock_training_processing_service = MagicMock()
        service.training_processing_service = mock_training_processing_service

        service.process_daily_operations()

        # Проверяем этап 1: посещаемость
        db_session.refresh(registered_student_for_today)
        assert registered_student_for_today.status == AttendanceStatus.PRESENT

        # Проверяем этап 2: финансы
        mock_training_processing_service.process_training.assert_called_once_with(
            tomorrow_training
        ) 