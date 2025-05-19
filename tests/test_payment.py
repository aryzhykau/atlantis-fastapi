import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import (
    Payment,
    PaymentHistory,
    UserRole,
    User,
    InvoiceStatus,
    Invoice,
    InvoiceType
)
from app.models.payment_history import OperationType
from app.services.payment import PaymentService


@pytest.fixture
def payment_data(test_client):
    return {
        "client_id": test_client.id,
        "amount": 100.0,
        "description": "Test payment"
    }


class TestPaymentService:
    def test_register_payment(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        service = PaymentService(db_session)
        initial_balance = test_client.balance or 0.0
        payment_amount = 100.0

        payment = service.register_payment(
            client_id=test_client.id,
            amount=payment_amount,
            description="Test payment registration",
            registered_by_id=test_admin.id
        )

        assert payment.client_id == test_client.id
        assert payment.amount == payment_amount
        assert payment.registered_by_id == test_admin.id
        assert payment.cancelled_at is None

        # Проверяем обновление баланса клиента
        test_client = db_session.merge(test_client)
        assert test_client.balance == initial_balance + payment_amount

        # Проверяем создание записи в истории
        payment_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id
        ).first()
        assert payment_history is not None
        assert payment_history.operation_type == OperationType.PAYMENT
        assert payment_history.amount == payment_amount
        assert payment_history.balance_before == initial_balance
        assert payment_history.balance_after == initial_balance + payment_amount

    def test_cancel_payment(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        service = PaymentService(db_session)
        
        # Регистрируем платеж
        payment_amount = 100.0
        payment = service.register_payment(
            client_id=test_client.id,
            amount=payment_amount,
            description="Test payment for cancellation",
            registered_by_id=test_admin.id
        )

        initial_balance = test_client.balance

        # Отменяем платеж
        cancelled_payment = service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id
        )

        assert cancelled_payment.cancelled_at is not None
        assert cancelled_payment.cancelled_by_id == test_admin.id

        # Проверяем обновление баланса клиента
        test_client = db_session.merge(test_client)
        assert test_client.balance == initial_balance - payment_amount

        # Проверяем создание записи в истории
        cancellation_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).first()
        assert cancellation_history is not None
        assert cancellation_history.amount == -payment_amount
        assert cancellation_history.balance_before == initial_balance
        assert cancellation_history.balance_after == initial_balance - payment_amount

    def test_get_client_balance(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        service = PaymentService(db_session)
        
        # Регистрируем несколько платежей
        payment1_amount = 100.0
        payment2_amount = 50.0

        service.register_payment(
            client_id=test_client.id,
            amount=payment1_amount,
            description="Test payment 1",
            registered_by_id=test_admin.id
        )

        service.register_payment(
            client_id=test_client.id,
            amount=payment2_amount,
            description="Test payment 2",
            registered_by_id=test_admin.id
        )

        # Проверяем баланс
        balance = service.get_client_balance(test_client.id)
        assert balance == payment1_amount + payment2_amount

    def test_get_client_payments(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        service = PaymentService(db_session)
        
        # Регистрируем несколько платежей
        for i in range(3):
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description=f"Test payment {i+1}",
                registered_by_id=test_admin.id
            )

        # Получаем список платежей
        payments = service.get_client_payments(test_client.id)
        assert len(payments) == 3

    def test_register_payment_validation(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест валидации при создании платежа"""
        service = PaymentService(db_session)

        # Проверка отрицательной суммы
        with pytest.raises(Exception) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=-100.0,
                description="Negative amount payment",
                registered_by_id=test_admin.id
            )
        assert "amount" in str(exc_info.value).lower()

        # Проверка нулевой суммы
        with pytest.raises(Exception) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=0.0,
                description="Zero amount payment",
                registered_by_id=test_admin.id
            )
        assert "amount" in str(exc_info.value).lower()

        # Проверка несуществующего клиента
        with pytest.raises(Exception) as exc_info:
            service.register_payment(
                client_id=99999,
                amount=100.0,
                description="Invalid client payment",
                registered_by_id=test_admin.id
            )
        assert "client" in str(exc_info.value).lower()

    def test_payment_access_rights(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест прав доступа при создании платежа"""
        service = PaymentService(db_session)

        # Создаем обычного клиента без прав администратора
        regular_user = User(
            first_name="Regular",
            last_name="User",
            email="regular@test.com",
            phone="1234567890",
            role=UserRole.CLIENT,
            date_of_birth=datetime.now().date()
        )
        db_session.add(regular_user)
        db_session.commit()

        # Проверяем, что клиент не может создавать платежи
        with pytest.raises(Exception) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description="Unauthorized payment",
                registered_by_id=regular_user.id
            )
        assert "permission" in str(exc_info.value).lower() or "admin" in str(exc_info.value).lower()

    def test_payment_with_invoice_processing(
        self,
        db_session: Session,
        test_client,
        test_admin,
        test_invoice  # нужно добавить эту фикстуру в conftest.py
    ):
        """Тест автоматического погашения инвойсов при платеже"""
        service = PaymentService(db_session)
        
        # Создаем платеж на сумму, достаточную для погашения инвойса
        payment = service.register_payment(
            client_id=test_client.id,
            amount=test_invoice.amount,
            description="Payment for invoice",
            registered_by_id=test_admin.id
        )

        # Проверяем, что инвойс был автоматически погашен
        db_session.refresh(test_invoice)
        assert test_invoice.status == InvoiceStatus.PAID
        assert test_invoice.paid_at is not None

        # Проверяем, что баланс клиента корректно обновлен
        db_session.refresh(test_client)
        assert test_client.balance == 0.0  # Весь платеж ушел на погашение инвойса

    def test_invoice_payment_order(
        self,
        db_session: Session,
        test_client,
        test_admin,
        test_subscription
    ):
        """Тест порядка погашения инвойсов (от старых к новым)"""
        service = PaymentService(db_session)
        
        # Создаем три инвойса с разными датами
        invoices = []
        for i in range(3):
            invoice = Invoice(
                client_id=test_client.id,
                subscription_id=test_subscription.id,
                amount=50.0,  # Каждый инвойс на 50
                description=f"Test invoice {i+1}",
                status=InvoiceStatus.UNPAID,
                type=InvoiceType.SUBSCRIPTION,
                created_by_id=test_admin.id,
                is_auto_renewal=False,
                created_at=datetime.utcnow() - timedelta(days=i)  # Разные даты создания
            )
            db_session.add(invoice)
            db_session.commit()
            db_session.refresh(invoice)
            invoices.append(invoice)
        
        # Создаем платеж на сумму, достаточную для погашения двух инвойсов
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Payment for multiple invoices",
            registered_by_id=test_admin.id
        )

        # Проверяем, что инвойсы погашены в правильном порядке
        db_session.refresh(invoices[2])  # Самый старый
        db_session.refresh(invoices[1])  # Средний
        db_session.refresh(invoices[0])  # Самый новый
        
        assert invoices[2].status == InvoiceStatus.PAID  # Самый старый должен быть оплачен
        assert invoices[1].status == InvoiceStatus.PAID  # Второй по старости тоже
        assert invoices[0].status == InvoiceStatus.UNPAID  # Новый должен остаться неоплаченным

    def test_payment_cancellation_with_invoices(
        self,
        db_session: Session,
        test_client,
        test_admin,
        test_invoice
    ):
        """Тест отмены платежа с автоматической отменой оплаты инвойсов"""
        service = PaymentService(db_session)
        
        # Создаем платеж и оплачиваем инвойс
        payment = service.register_payment(
            client_id=test_client.id,
            amount=test_invoice.amount,
            description="Payment for invoice",
            registered_by_id=test_admin.id
        )
        
        # Проверяем, что инвойс оплачен
        db_session.refresh(test_invoice)
        assert test_invoice.status == InvoiceStatus.PAID
        
        # Отменяем платеж
        cancelled_payment = service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"  # Добавляем причину отмены
        )
        
        # Проверяем, что инвойс снова стал неоплаченным
        db_session.refresh(test_invoice)
        assert test_invoice.status == InvoiceStatus.UNPAID
        assert test_invoice.paid_at is None
        
        # Проверяем запись об отмене
        cancellation_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).first()
        assert cancellation_history is not None
        assert cancellation_history.description == "Test cancellation"

    def test_payment_history_access(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест доступа к истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем обычного пользователя
        regular_user = User(
            first_name="Regular",
            last_name="User",
            email="regular@test.com",
            phone="1234567890",
            role=UserRole.CLIENT,
            date_of_birth=datetime.now().date()
        )
        db_session.add(regular_user)
        db_session.commit()

        # Создаем платеж
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_admin.id
        )

        # Проверяем доступ к истории для админа
        history_admin = service.get_payment_history(user_id=test_admin.id, client_id=test_client.id)
        assert len(history_admin) > 0

        # Проверяем отсутствие доступа для обычного пользователя
        with pytest.raises(HTTPException) as exc_info:
            service.get_payment_history(user_id=regular_user.id, client_id=test_client.id)
        assert exc_info.value.status_code == 403

    def test_trainer_payment_creation(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест создания платежа тренером через отметку присутствия"""
        service = PaymentService(db_session)
        
        # Создаем тренера
        trainer = User(
            first_name="Test",
            last_name="Trainer",
            email="trainer@test.com",
            phone="1111111111",  # Уникальный номер
            role=UserRole.TRAINER,
            date_of_birth=datetime.now().date()
        )
        db_session.add(trainer)
        db_session.commit()

        # Тренер создает платеж через отметку присутствия
        payment = service.register_training_payment(
            client_id=test_client.id,
            amount=100.0,
            training_id=1,  # ID тренировки
            registered_by_id=trainer.id
        )

        assert payment.registered_by_id == trainer.id
        assert payment.amount == 100.0
        assert "training" in payment.description.lower()

        # Проверяем обновление баланса
        db_session.refresh(test_client)
        assert test_client.balance == 100.0

    def test_payment_cancellation_description(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест описания при отмене платежа"""
        service = PaymentService(db_session)
        
        # Регистрируем платеж
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_admin.id
        )

        # Отменяем платеж с описанием
        cancellation_description = "Ошибка в сумме платежа"
        cancelled_payment = service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason=cancellation_description
        )

        # Проверяем запись в истории
        cancellation_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).first()
        
        assert cancellation_history is not None
        assert cancellation_history.description == cancellation_description

    def test_partial_invoice_payment_history(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест истории платежей при частичной оплате инвойса"""
        service = PaymentService(db_session)
        
        # Создаем инвойс на 1000
        invoice = Invoice(
            client_id=test_client.id,
            amount=1000.0,
            type=InvoiceType.SUBSCRIPTION,
            status=InvoiceStatus.UNPAID,
            description="Test invoice",
            created_by_id=test_admin.id,
            created_at=datetime.utcnow()
        )
        db_session.add(invoice)
        db_session.commit()

        # Делаем частичный платеж
        partial_amount = 400.0
        payment = service.register_payment(
            client_id=test_client.id,
            amount=partial_amount,
            description="Partial payment",
            registered_by_id=test_admin.id
        )

        # Проверяем историю
        payment_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.PAYMENT
        ).first()

        assert payment_history is not None
        assert payment_history.amount == partial_amount
        assert "Partial payment" in payment_history.description
        
        # Проверяем статус инвойса - должен остаться неоплаченным, так как оплата частичная
        db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.UNPAID
        assert invoice.paid_at is None  # Дата оплаты должна быть пустой
        assert invoice.payment_id is None  # Связь с платежом не должна устанавливаться при частичной оплате

    def test_payment_description_validation(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест валидации описания платежа"""
        service = PaymentService(db_session)

        # Проверка пустого описания
        with pytest.raises(HTTPException) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description="",
                registered_by_id=test_admin.id
            )
        assert exc_info.value.status_code == 400
        assert "description" in str(exc_info.value.detail).lower()

        # Проверка слишком длинного описания (более 500 символов)
        long_description = "A" * 501
        with pytest.raises(HTTPException) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description=long_description,
                registered_by_id=test_admin.id
            )
        assert exc_info.value.status_code == 400
        assert "description" in str(exc_info.value.detail).lower()


class TestPaymentEndpoints:
    def test_create_payment(self, client, auth_headers, payment_data):
        response = client.post(
            "/payments/",
            json=payment_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["amount"] == payment_data["amount"]
        assert response.json()["description"] == payment_data["description"]

    def test_cancel_payment(
        self,
        client,
        auth_headers,
        test_payment
    ):
        response = client.delete(
            f"/payments/{test_payment.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["cancelled_at"] is not None

    def test_get_client_payments(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        service = PaymentService(db_session)
        
        # Создаем несколько платежей
        for i in range(3):
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description=f"Test payment {i+1}",
                registered_by_id=test_admin.id
            )

        response = client.get(
            f"/payments/client/{test_client.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_get_client_balance(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        service = PaymentService(db_session)
        
        # Регистрируем платеж
        payment_amount = 100.0
        service.register_payment(
            client_id=test_client.id,
            amount=payment_amount,
            description="Test payment",
            registered_by_id=test_admin.id
        )

        response = client.get(
            f"/payments/client/{test_client.id}/balance",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["balance"] == payment_amount 