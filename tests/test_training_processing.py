import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.models import (
    Invoice, InvoiceStatus, InvoiceType, AttendanceStatus,
    StudentSubscription, RealTraining, RealTrainingStudent, User, UserRole
)
from app.services.training_processing import TrainingProcessingService


class TestTrainingProcessingService:
    """Тесты для сервиса обработки тренировок наперед"""

    def test_get_tomorrow_trainings(
        self,
        db_session: Session,
        test_tomorrow_training,
        test_tomorrow_training_no_subscription,
        test_cancelled_training
    ):
        """Тест получения тренировок на завтра"""
        service = TrainingProcessingService(db_session)
        trainings = service.get_tomorrow_trainings()
        
        # Должны быть только неотмененные тренировки на завтра
        assert len(trainings) == 2
        training_ids = [t.id for t in trainings]
        assert test_tomorrow_training.id in training_ids
        assert test_tomorrow_training_no_subscription.id in training_ids
        assert test_cancelled_training.id not in training_ids  # Отмененная тренировка исключена

    def test_get_active_subscription_with_active_subscription(
        self,
        db_session: Session,
        test_student_subscription,
        test_tomorrow_training
    ):
        """Тест получения активного абонемента - есть активный абонемент"""
        service = TrainingProcessingService(db_session)
        subscription = service.get_active_subscription(
            test_student_subscription.student_id,
            test_tomorrow_training.training_date
        )
        
        assert subscription is not None
        assert subscription.id == test_student_subscription.id
        assert subscription.sessions_left > 0

    def test_get_active_subscription_without_subscription(
        self,
        db_session: Session,
        test_student,
        test_tomorrow_training
    ):
        """Тест получения активного абонемента - нет абонемента"""
        service = TrainingProcessingService(db_session)
        subscription = service.get_active_subscription(
            test_student.id,
            test_tomorrow_training.training_date
        )
        
        assert subscription is None

    def test_get_active_subscription_expired(
        self,
        db_session: Session,
        test_student_subscription_expired,
        test_tomorrow_training
    ):
        """Тест получения активного абонемента - истекший абонемент"""
        service = TrainingProcessingService(db_session)
        subscription = service.get_active_subscription(
            test_student_subscription_expired.student_id,
            test_tomorrow_training.training_date
        )
        
        assert subscription is None

    def test_check_existing_invoice_exists(
        self,
        db_session: Session,
        test_student,
        test_tomorrow_training,
        test_admin
    ):
        """Тест проверки существования инвойса - инвойс существует"""
        # Создаем инвойс
        invoice = Invoice(
            client_id=test_student.client_id,
            student_id=test_student.id,
            training_id=test_tomorrow_training.id,
            type=InvoiceType.TRAINING,
            amount=100.0,
            description="Test invoice",
            status=InvoiceStatus.UNPAID
        )
        db_session.add(invoice)
        db_session.commit()
        
        service = TrainingProcessingService(db_session)
        exists = service.check_existing_invoice(test_student.id, test_tomorrow_training.id)
        
        assert exists is True

    def test_check_existing_invoice_not_exists(
        self,
        db_session: Session,
        test_student,
        test_tomorrow_training
    ):
        """Тест проверки существования инвойса - инвойс не существует"""
        service = TrainingProcessingService(db_session)
        exists = service.check_existing_invoice(test_student.id, test_tomorrow_training.id)
        
        assert exists is False

    def test_process_student_with_active_subscription(
        self,
        db_session: Session,
        test_real_training_student_with_subscription,
        test_tomorrow_training
    ):
        """Тест обработки студента с активным абонементом"""
        service = TrainingProcessingService(db_session)
        initial_sessions = test_real_training_student_with_subscription.subscription.sessions_left
        
        result = service.process_student_training(
            test_real_training_student_with_subscription,
            test_tomorrow_training
        )
        
        assert result["action"] == "deduct_session"
        assert "Списано занятие" in result["details"]
        assert result["error"] is None
        
        # Проверяем, что занятие списано
        db_session.refresh(test_real_training_student_with_subscription.subscription)
        assert test_real_training_student_with_subscription.subscription.sessions_left == initial_sessions - 1

    def test_process_student_without_subscription(
        self,
        db_session: Session,
        test_real_training_student_without_subscription,
        test_tomorrow_training
    ):
        """Тест обработки студента без абонемента"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_student_training(
            test_real_training_student_without_subscription,
            test_tomorrow_training
        )
        
        assert result["action"] == "create_invoice"
        assert "Создан инвойс" in result["details"]
        assert result["error"] is None
        
        # Проверяем, что инвойс создан
        invoice = db_session.query(Invoice).filter(
            Invoice.student_id == test_real_training_student_without_subscription.student_id,
            Invoice.training_id == test_tomorrow_training.id
        ).first()
        
        assert invoice is not None
        assert invoice.type == InvoiceType.TRAINING
        assert invoice.amount == test_tomorrow_training.training_type.price

    def test_process_student_safe_cancellation(
        self,
        db_session: Session,
        test_student_training_safe_cancellation,
        test_tomorrow_training
    ):
        """Тест обработки студента с безопасной отменой"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_student_training(
            test_student_training_safe_cancellation,
            test_tomorrow_training
        )
        
        assert result["action"] == "skip_safe_cancellation"
        assert "Безопасная отмена" in result["details"]
        assert result["error"] is None

    def test_process_student_penalty_cancellation(
        self,
        db_session: Session,
        test_student_training_penalty_cancellation_no_subscription,
        test_tomorrow_training
    ):
        """Тест обработки студента со штрафной отменой без абонемента"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_student_training(
            test_student_training_penalty_cancellation_no_subscription,
            test_tomorrow_training
        )
        
        # Штрафная отмена должна создать инвойс
        assert result["action"] == "create_invoice"
        assert "Создан инвойс" in result["details"]
        assert result["error"] is None

    def test_process_student_penalty_cancellation_with_subscription(
        self,
        db_session: Session,
        test_student_training_penalty_cancellation_with_subscription,
        test_tomorrow_training
    ):
        """Тест обработки студента со штрафной отменой с абонементом"""
        service = TrainingProcessingService(db_session)
        initial_sessions = test_student_training_penalty_cancellation_with_subscription.subscription.sessions_left
        
        result = service.process_student_training(
            test_student_training_penalty_cancellation_with_subscription,
            test_tomorrow_training
        )
        
        # Штрафная отмена должна списать занятие с абонемента
        assert result["action"] == "deduct_session"
        assert "Списано занятие" in result["details"]
        assert result["error"] is None
        
        # Проверяем, что занятие списано
        db_session.refresh(test_student_training_penalty_cancellation_with_subscription.subscription)
        assert test_student_training_penalty_cancellation_with_subscription.subscription.sessions_left == initial_sessions - 1

    def test_process_student_free_training(
        self,
        db_session: Session,
        test_real_training_student_no_subscription_type,
        test_tomorrow_training_no_subscription
    ):
        """Тест обработки студента на бесплатной тренировке"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_student_training(
            test_real_training_student_no_subscription_type,
            test_tomorrow_training_no_subscription
        )
        
        assert result["action"] == "skip_free_training"
        assert "Бесплатная тренировка" in result["details"]
        assert result["error"] is None

    def test_process_student_expired_subscription(
        self,
        db_session: Session,
        test_real_training_student_expired_subscription,
        test_tomorrow_training
    ):
        """Тест обработки студента с истекшим абонементом"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_student_training(
            test_real_training_student_expired_subscription,
            test_tomorrow_training
        )
        
        # Должен быть создан инвойс, так как абонемент истек
        assert result["action"] == "create_invoice"
        assert "Создан инвойс" in result["details"]
        assert result["error"] is None

    def test_process_training_multiple_students(
        self,
        db_session: Session,
        test_real_training_multiple_students,
        test_tomorrow_training
    ):
        """Тест обработки тренировки с несколькими студентами"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_training(test_tomorrow_training)
        
        assert result["students_processed"] == 2
        assert result["sessions_deducted"] == 1  # Один студент с абонементом
        assert result["invoices_created"] == 1   # Один студент без абонемента
        assert result["errors"] == 0
        assert len(result["student_results"]) == 2

    def test_process_tomorrow_trainings_success(
        self,
        db_session: Session,
        test_admin,
        test_real_training_student_with_subscription,
        test_real_training_student_without_subscription,
        test_tomorrow_training
    ):
        """Тест успешной обработки всех тренировок на завтра"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_tomorrow_trainings(test_admin.id)
        
        assert result["trainings_processed"] == 1
        assert result["total_students_processed"] == 2
        assert result["total_sessions_deducted"] == 2  # Оба студента с активными абонементами
        assert result["total_invoices_created"] == 0   # Инвойсы не создаются, так как есть абонементы
        assert result["total_errors"] == 0
        assert result["message"] == "Обработка завершена успешно"
        assert "error" not in result

    def test_process_tomorrow_trainings_no_trainings(
        self,
        db_session: Session,
        test_admin
    ):
        """Тест обработки когда нет тренировок на завтра"""
        service = TrainingProcessingService(db_session)
        
        result = service.process_tomorrow_trainings(test_admin.id)
        
        assert result["trainings_processed"] == 0
        assert result["total_students_processed"] == 0
        assert result["message"] == "Нет тренировок на завтра для обработки"
        assert "error" not in result

    def test_process_tomorrow_trainings_not_admin(
        self,
        db_session: Session,
        test_trainer
    ):
        """Тест обработки неадминистратором - должно вызвать ошибку"""
        service = TrainingProcessingService(db_session)
        
        with pytest.raises(ValueError, match="Only admins can process training invoices"):
            service.process_tomorrow_trainings(test_trainer.id)


class TestTrainingProcessingEndpoints:
    """Тесты для эндпоинтов обработки тренировок"""

    def test_generate_invoices_endpoint_success(
        self,
        client,
        test_admin,
        test_real_training_student_with_subscription,
        test_real_training_student_without_subscription,
        test_tomorrow_training,
        api_key_headers
    ):
        """Тест успешного вызова эндпоинта генерации инвойсов"""
        response = client.post("/cron/generate-invoices", headers=api_key_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert data["result"]["trainings_processed"] == 1
        assert data["result"]["total_students_processed"] == 2

    def test_generate_invoices_endpoint_no_admin(
        self,
        client,
        api_key_headers,
        db_session
    ):
        """Тест вызова эндпоинта без администратора в системе"""
        # Удаляем всех админов
        db_session.query(User).filter(User.role == UserRole.ADMIN).delete()
        db_session.commit()
        
        response = client.post("/cron/generate-invoices", headers=api_key_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No admin user found" in data["error"]

    def test_generate_invoices_endpoint_no_api_key(
        self,
        client,
        test_admin
    ):
        """Тест вызова эндпоинта без API ключа"""
        response = client.post("/cron/generate-invoices")
        
        assert response.status_code == 403  # Должен быть запрещен доступ

    def test_generate_invoices_endpoint_invalid_api_key(
        self,
        client,
        test_admin
    ):
        """Тест вызова эндпоинта с неверным API ключом"""
        headers = {"X-API-Key": "invalid_key"}
        response = client.post("/cron/generate-invoices", headers=headers)
        
        assert response.status_code == 403  # Должен быть запрещен доступ 