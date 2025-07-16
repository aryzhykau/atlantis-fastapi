import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Payment, PaymentHistory, User, UserRole
from app.models.payment_history import OperationType
from app.crud import payment as crud
from app.schemas.payment import PaymentCreate, PaymentUpdate


class TestPaymentCRUD:
    """Тесты для CRUD операций с платежами"""

    def test_get_payment(self, db_session: Session, test_payment: Payment):
        """Тест получения платежа по ID"""
        payment = crud.get_payment(db_session, test_payment.id)
        
        assert payment is not None
        assert payment.id == test_payment.id
        assert payment.client_id == test_payment.client_id
        assert payment.amount == test_payment.amount

    def test_get_payment_not_found(self, db_session: Session):
        """Тест получения несуществующего платежа"""
        payment = crud.get_payment(db_session, 99999)
        assert payment is None

    def test_get_payments(self, db_session: Session, test_payment: Payment):
        """Тест получения списка платежей"""
        payments = crud.get_payments(db_session)
        
        assert len(payments) >= 1
        payment_ids = [p.id for p in payments]
        assert test_payment.id in payment_ids

    def test_get_payments_with_skip_limit(self, db_session: Session, test_payment: Payment):
        """Тест получения платежей с пагинацией"""
        payments = crud.get_payments(db_session, skip=0, limit=1)
        
        assert len(payments) <= 1
        assert len(payments) >= 0

    def test_get_payments_with_filters(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения платежей с фильтрами"""
        # Создаем платеж
        payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=150.0,
            description="Filtered payment",
            registered_by_id=test_admin.id
        )
        db_session.commit()
        
        # Тестируем фильтр по client_id
        client_payments = crud.get_payments(db_session, client_id=test_client.id)
        assert len(client_payments) >= 1
        assert all(p.client_id == test_client.id for p in client_payments)
        
        # Тестируем фильтр по registered_by_id
        admin_payments = crud.get_payments(db_session, registered_by_id=test_admin.id)
        assert len(admin_payments) >= 1
        assert all(p.registered_by_id == test_admin.id for p in admin_payments)

    def test_create_payment(self, db_session: Session, test_client: User, test_admin: User):
        """Тест создания платежа"""
        payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=150.0,
            description="New test payment",
            registered_by_id=test_admin.id
        )
        
        assert payment is not None
        assert payment.client_id == test_client.id
        assert payment.amount == 150.0
        assert payment.description == "New test payment"
        assert payment.registered_by_id == test_admin.id
        assert payment.cancelled_at is None

    def test_update_payment(self, db_session: Session, test_payment: Payment):
        """Тест обновления платежа"""
        new_description = "Updated payment description"
        new_amount = 250.0
        
        update_data = PaymentUpdate(
            description=new_description,
            amount=new_amount
        )
        
        updated_payment = crud.update_payment(db_session, test_payment.id, update_data)
        
        assert updated_payment is not None
        assert updated_payment.description == new_description
        assert updated_payment.amount == new_amount

    def test_update_payment_not_found(self, db_session: Session):
        """Тест обновления несуществующего платежа"""
        update_data = PaymentUpdate(description="Updated description")
        updated_payment = crud.update_payment(db_session, 99999, update_data)
        
        assert updated_payment is None

    def test_cancel_payment(self, db_session: Session, test_payment: Payment, test_admin: User):
        """Тест отмены платежа"""
        payment_id = test_payment.id
        
        # Проверяем, что платеж активен
        payment = crud.get_payment(db_session, payment_id)
        assert payment.cancelled_at is None
        
        # Отменяем платеж
        cancelled_payment = crud.cancel_payment(
            db_session, 
            payment_id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )
        
        assert cancelled_payment is not None
        assert cancelled_payment.cancelled_at is not None
        assert cancelled_payment.cancelled_by_id == test_admin.id
        assert cancelled_payment.cancellation_reason == "Test cancellation"

    def test_cancel_payment_not_found(self, db_session: Session, test_admin: User):
        """Тест отмены несуществующего платежа"""
        cancelled_payment = crud.cancel_payment(
            db_session, 
            99999,
            cancelled_by_id=test_admin.id
        )
        
        assert cancelled_payment is None

    def test_cancel_already_cancelled_payment(self, db_session: Session, test_payment: Payment, test_admin: User):
        """Тест отмены уже отмененного платежа"""
        # Отменяем платеж первый раз
        cancelled_payment = crud.cancel_payment(
            db_session, 
            test_payment.id,
            cancelled_by_id=test_admin.id
        )
        
        # Пытаемся отменить снова
        cancelled_again = crud.cancel_payment(
            db_session, 
            test_payment.id,
            cancelled_by_id=test_admin.id
        )
        
        assert cancelled_again is not None
        assert cancelled_again.cancelled_at is not None

    def test_delete_payment(self, db_session: Session, test_payment: Payment, test_admin: User):
        """Тест удаления платежа"""
        payment_id = test_payment.id
        
        # Сначала отменяем платеж
        crud.cancel_payment(db_session, payment_id, cancelled_by_id=test_admin.id)
        db_session.commit()
        
        # Проверяем, что платеж существует и отменен
        payment = crud.get_payment(db_session, payment_id)
        assert payment is not None
        assert payment.cancelled_at is not None
        
        # Удаляем платеж
        deleted = crud.delete_payment(db_session, payment_id)
        db_session.commit()
        assert deleted is True
        
        # Проверяем, что платеж удален
        payment = crud.get_payment(db_session, payment_id)
        assert payment is None

    def test_delete_payment_not_found(self, db_session: Session):
        """Тест удаления несуществующего платежа"""
        deleted = crud.delete_payment(db_session, 99999)
        assert deleted is False

    def test_delete_active_payment(self, db_session: Session, test_payment: Payment):
        """Тест удаления активного платежа (должно вернуть False)"""
        deleted = crud.delete_payment(db_session, test_payment.id)
        assert deleted is False

    def test_get_client_payments(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения платежей клиента"""
        # Создаем несколько платежей для клиента
        payment1 = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=100.0,
            description="Payment 1",
            registered_by_id=test_admin.id
        )
        
        payment2 = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=200.0,
            description="Payment 2",
            registered_by_id=test_admin.id
        )
        
        db_session.commit()
        
        # Получаем платежи клиента
        client_payments = crud.get_client_payments(db_session, test_client.id)
        
        assert len(client_payments) >= 2
        payment_ids = [p.id for p in client_payments]
        assert payment1.id in payment_ids
        assert payment2.id in payment_ids

    def test_get_client_payments_empty(self, db_session: Session, test_client: User):
        """Тест получения платежей клиента без платежей"""
        # Используем существующую фикстуру test_client
        # Сначала удаляем все платежи этого клиента, чтобы проверить пустой список
        existing_payments = crud.get_client_payments(db_session, test_client.id)
        for payment in existing_payments:
            db_session.delete(payment)
        db_session.commit()
        
        client_payments = crud.get_client_payments(db_session, test_client.id)
        assert len(client_payments) == 0

    def test_get_payment_count(self, db_session: Session, test_client: User, test_admin: User):
        """Тест подсчета количества платежей"""
        # Создаем несколько платежей
        for i in range(3):
            crud.create_payment(
                db_session,
                client_id=test_client.id,
                amount=100.0,
                description=f"Payment {i+1}",
                registered_by_id=test_admin.id
            )
        
        db_session.commit()
        
        # Подсчитываем платежи клиента
        count = crud.get_payment_count(db_session, client_id=test_client.id)
        assert count >= 3
        
        # Подсчитываем платежи администратора
        admin_count = crud.get_payment_count(db_session, registered_by_id=test_admin.id)
        assert admin_count >= 3

    def test_get_active_payments(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения активных платежей"""
        # Создаем активный платеж
        active_payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=100.0,
            description="Active payment",
            registered_by_id=test_admin.id
        )
        
        # Создаем отмененный платеж
        cancelled_payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=200.0,
            description="Cancelled payment",
            registered_by_id=test_admin.id
        )
        
        db_session.commit()
        
        # Отменяем второй платеж
        crud.cancel_payment(db_session, cancelled_payment.id, cancelled_by_id=test_admin.id)
        
        # Получаем активные платежи
        active_payments = crud.get_active_payments(db_session, client_id=test_client.id)
        
        assert len(active_payments) >= 1
        assert all(p.cancelled_at is None for p in active_payments)
        assert active_payment.id in [p.id for p in active_payments]

    def test_get_cancelled_payments(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения отмененных платежей"""
        # Создаем платеж и отменяем его
        payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=100.0,
            description="Cancelled payment",
            registered_by_id=test_admin.id
        )
        db_session.commit()
        
        crud.cancel_payment(db_session, payment.id, cancelled_by_id=test_admin.id)
        
        # Получаем отмененные платежи
        cancelled_payments = crud.get_cancelled_payments(db_session, client_id=test_client.id)
        
        assert len(cancelled_payments) >= 1
        assert all(p.cancelled_at is not None for p in cancelled_payments)
        assert payment.id in [p.id for p in cancelled_payments]

    def test_get_payment_history(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения истории платежей"""
        # Создаем платеж
        payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=100.0,
            description="Test payment for history",
            registered_by_id=test_admin.id
        )
        db_session.commit()
        
        # Создаем запись в истории
        history = PaymentHistory(
            payment_id=payment.id,
            client_id=test_client.id,
            amount=100.0,
            balance_before=0.0,
            balance_after=100.0,
            operation_type=OperationType.PAYMENT,
            created_by_id=test_admin.id
        )
        db_session.add(history)
        db_session.commit()
        
        # Получаем историю
        payment_history = crud.get_payment_history(db_session, test_client.id)
        
        assert len(payment_history) >= 1
        history_record = payment_history[0]
        assert history_record.payment_id == payment.id
        assert history_record.client_id == test_client.id
        assert history_record.amount == 100.0

    def test_get_payment_history_with_pagination(self, db_session: Session, test_client: User, test_admin: User):
        """Тест получения истории платежей с пагинацией"""
        # Создаем несколько записей в истории
        for i in range(5):
            payment = crud.create_payment(
                db_session,
                client_id=test_client.id,
                amount=100.0,
                description=f"Payment {i+1}",
                registered_by_id=test_admin.id
            )
            
            history = PaymentHistory(
                payment_id=payment.id,
                client_id=test_client.id,
                amount=100.0,
                balance_before=0.0,
                balance_after=100.0,
                operation_type=OperationType.PAYMENT,
                created_by_id=test_admin.id
            )
            db_session.add(history)
        
        db_session.commit()
        
        # Получаем историю с пагинацией
        payment_history = crud.get_payment_history(db_session, test_client.id, skip=0, limit=3)
        
        assert len(payment_history) <= 3
        assert len(payment_history) >= 1

    def test_payment_crud_integration(self, db_session: Session, test_client: User, test_admin: User):
        """Интеграционный тест CRUD операций с платежами"""
        # 1. Создаем платеж
        payment = crud.create_payment(
            db_session,
            client_id=test_client.id,
            amount=150.0,
            description="Integration test payment",
            registered_by_id=test_admin.id
        )
        db_session.commit()
        
        assert payment is not None
        assert payment.client_id == test_client.id
        assert payment.amount == 150.0
        
        # 2. Получаем платеж
        retrieved_payment = crud.get_payment(db_session, payment.id)
        assert retrieved_payment is not None
        assert retrieved_payment.id == payment.id
        
        # 3. Обновляем платеж
        update_data = PaymentUpdate(amount=200.0, description="Updated payment")
        updated_payment = crud.update_payment(db_session, payment.id, update_data)
        assert updated_payment.amount == 200.0
        
        # 4. Отменяем платеж
        cancelled_payment = crud.cancel_payment(
            db_session, 
            payment.id, 
            cancelled_by_id=test_admin.id,
            cancellation_reason="Integration test cancellation"
        )
        assert cancelled_payment.cancelled_at is not None
        
        # 5. Удаляем платеж
        deleted = crud.delete_payment(db_session, payment.id)
        db_session.commit()
        assert deleted is True
        
        # 6. Проверяем, что платеж удален
        deleted_payment = crud.get_payment(db_session, payment.id)
        assert deleted_payment is None 