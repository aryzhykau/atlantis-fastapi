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
        
        # Создаем платеж
        payment = service.register_payment(
            client_id=test_client.id,
            amount=test_invoice.amount,
            description="Payment for invoice",
            registered_by_id=test_admin.id
        )
        
        # Проверяем, что инвойс оплачен автоматически
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
        
        # Проверяем запись об отмене (сейчас отменяется с припиской "Частичная отмена платежа")
        cancellation_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).first()
        assert cancellation_history is not None
        assert cancellation_history.description.endswith("Test cancellation)")
        assert "отмена платежа" in cancellation_history.description

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
        

    def test_payment_description_validation(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест валидации описания платежа"""
        service = PaymentService(db_session)

        # Проверка слишком длинного описания (более 500 символов)
        long_description = "A" * 501
        with pytest.raises(HTTPException) as exc_info:
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                registered_by_id=test_admin.id,
                description=long_description
            )
        assert exc_info.value.status_code == 400
        assert "description" in str(exc_info.value.detail).lower()
        
        # Проверка успешного создания с пустым описанием
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            registered_by_id=test_admin.id,
            description=""
        )
        assert payment is not None
        assert payment.description == ""
        
        # Проверка успешного создания с None вместо описания
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            registered_by_id=test_admin.id,
            description=None
        )
        assert payment is not None
        assert payment.description is None

    def test_cancel_payment_with_sufficient_balance(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест отмены платежа, когда баланс достаточен (просто уменьшение баланса)"""
        service = PaymentService(db_session)
        
        # Регистрируем платеж
        payment_amount = 100.0
        payment = service.register_payment(
            client_id=test_client.id,
            amount=payment_amount,
            description="Test payment for cancellation",
            registered_by_id=test_admin.id
        )

        # Добавляем дополнительный платеж, чтобы увеличить баланс
        additional_amount = 50.0
        service.register_payment(
            client_id=test_client.id,
            amount=additional_amount,
            description="Additional payment",
            registered_by_id=test_admin.id
        )

        # Проверяем, что баланс теперь больше суммы первого платежа
        db_session.refresh(test_client)
        initial_balance = test_client.balance
        assert initial_balance > payment_amount

        # Создаем инвойс
        invoice = Invoice(
            client_id=test_client.id,
            amount=20.0,
            description="Test invoice",
            status=InvoiceStatus.UNPAID,
            type=InvoiceType.SUBSCRIPTION,
            created_by_id=test_admin.id,
            is_auto_renewal=False
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        # Запускаем процесс погашения инвойсов вручную
        # Получаем неоплаченные инвойсы
        unpaid_invoices = db_session.query(Invoice).filter(
            Invoice.client_id == test_client.id,
            Invoice.status == InvoiceStatus.UNPAID
        ).order_by(Invoice.created_at.asc()).all()
        
        # Вручную погашаем инвойс
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        db_session.refresh(test_client)

        # Создаем запись в истории платежей с типом INVOICE_PAYMENT
        history = PaymentHistory(
            client_id=test_client.id,
            payment_id=None,
            invoice_id=invoice.id,
            operation_type=OperationType.INVOICE_PAYMENT,
            amount=-invoice.amount,
            balance_before=initial_balance,
            balance_after=initial_balance - invoice.amount,
            created_by_id=test_admin.id,
            description=f"Оплата инвойса #{invoice.id}"
        )
        db_session.add(history)
        db_session.commit()
        
        # Обновляем баланс клиента
        test_client.balance = initial_balance - invoice.amount
        db_session.add(test_client)
        db_session.commit()
        db_session.refresh(test_client)
        
        # Проверяем, что инвойс оплачен
        assert invoice.status == InvoiceStatus.PAID
        initial_balance = test_client.balance

        # Отменяем первый платеж
        cancelled_payment = service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )

        # Проверяем отмену платежа
        assert cancelled_payment.cancelled_at is not None
        assert cancelled_payment.cancelled_by_id == test_admin.id

        # Проверяем обновление баланса клиента - уменьшился на сумму первого платежа
        db_session.refresh(test_client)
        assert test_client.balance == initial_balance - payment_amount

        # Проверяем, что инвойс остался оплаченным (т.к. баланса хватало)
        db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID

        # Проверяем создание записи в истории
        cancellation_history = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).first()
        assert cancellation_history is not None
        assert cancellation_history.amount == -payment_amount
        assert cancellation_history.balance_before == initial_balance
        assert cancellation_history.balance_after == initial_balance - payment_amount

    def test_cancel_payment_with_insufficient_balance(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест отмены платежа, когда баланс недостаточен (отмена инвойсов)"""
        service = PaymentService(db_session)
        
        # Регистрируем платеж
        payment_amount = 200.0
        payment = service.register_payment(
            client_id=test_client.id,
            amount=payment_amount,
            description="Test payment for cancellation",
            registered_by_id=test_admin.id
        )

        # Создаем два инвойса
        invoice1 = Invoice(
            client_id=test_client.id,
            amount=120.0,
            description="Test invoice 1",
            status=InvoiceStatus.UNPAID,
            type=InvoiceType.SUBSCRIPTION,
            created_by_id=test_admin.id,
            is_auto_renewal=False
        )
        
        invoice2 = Invoice(
            client_id=test_client.id,
            amount=80.0,
            description="Test invoice 2",
            status=InvoiceStatus.UNPAID,
            type=InvoiceType.SUBSCRIPTION,
            created_by_id=test_admin.id,
            is_auto_renewal=False
        )
        
        db_session.add(invoice1)
        db_session.add(invoice2)
        db_session.commit()
        db_session.refresh(invoice1)
        db_session.refresh(invoice2)
        db_session.refresh(test_client)
        
        # Вручную погашаем инвойсы и создаем записи в истории
        initial_balance = test_client.balance
        
        # Погашаем первый инвойс
        invoice1.status = InvoiceStatus.PAID
        invoice1.paid_at = datetime.utcnow()
        db_session.add(invoice1)
        db_session.commit()
        
        # Создаем запись в истории
        history1 = PaymentHistory(
            client_id=test_client.id,
            payment_id=None,
            invoice_id=invoice1.id,
            operation_type=OperationType.INVOICE_PAYMENT,
            amount=-invoice1.amount,
            balance_before=initial_balance,
            balance_after=initial_balance - invoice1.amount,
            created_by_id=test_admin.id,
            description=f"Оплата инвойса #{invoice1.id}"
        )
        db_session.add(history1)
        
        # Обновляем баланс клиента
        test_client.balance = initial_balance - invoice1.amount
        db_session.add(test_client)
        db_session.commit()
        db_session.refresh(test_client)
        
        # Погашаем второй инвойс
        current_balance = test_client.balance
        invoice2.status = InvoiceStatus.PAID
        invoice2.paid_at = datetime.utcnow()
        db_session.add(invoice2)
        db_session.commit()
        
        # Создаем запись в истории
        history2 = PaymentHistory(
            client_id=test_client.id,
            payment_id=None,
            invoice_id=invoice2.id,
            operation_type=OperationType.INVOICE_PAYMENT,
            amount=-invoice2.amount,
            balance_before=current_balance,
            balance_after=current_balance - invoice2.amount,
            created_by_id=test_admin.id,
            description=f"Оплата инвойса #{invoice2.id}"
        )
        db_session.add(history2)
        
        # Обновляем баланс клиента
        test_client.balance = current_balance - invoice2.amount
        db_session.add(test_client)
        db_session.commit()
        db_session.refresh(test_client)
        
        # Инвойсы должны быть оплачены из баланса
        db_session.refresh(invoice1)
        db_session.refresh(invoice2)
        assert invoice1.status == InvoiceStatus.PAID
        assert invoice2.status == InvoiceStatus.PAID
        
        # Баланс должен быть 0
        assert test_client.balance == 0.0
        
        # Добавляем маленький платеж, чтобы был недостаточный для отмены баланс
        small_payment = service.register_payment(
            client_id=test_client.id,
            amount=50.0,
            description="Additional small payment",
            registered_by_id=test_admin.id
        )
        
        db_session.refresh(test_client)
        initial_balance = test_client.balance
        assert initial_balance == 50.0  # Подтверждаем, что баланс теперь 50
        
        # Отменяем первый платеж на 200р
        cancelled_payment = service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation with insufficient balance"
        )
        
        # Проверяем отмену платежа
        assert cancelled_payment.cancelled_at is not None
        
        # Проверяем, что баланс обнулился
        db_session.refresh(test_client)
        
        # Проверяем статус инвойсов
        db_session.refresh(invoice1)
        db_session.refresh(invoice2)
        
        # Оба инвойса должны быть отменены
        assert invoice1.status == InvoiceStatus.UNPAID
        assert invoice2.status == InvoiceStatus.UNPAID
        
        # Последний инвойс должен дать частичный возврат на баланс 
        # (поскольку sum(инвойсы) - баланс < стоимость последнего инвойса)
        # 200 - 50 = 150, 150 - 120 = 30
        # 80 - 30 = 50р должно быть на балансе
        assert test_client.balance > 0.0
        
        # Проверяем записи в истории
        cancellation_histories = db_session.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.operation_type == OperationType.CANCELLATION
        ).all()
        
        assert len(cancellation_histories) > 1  # Должно быть несколько записей
        
        # Проверяем, что первая запись - списание всего баланса
        first_history = [h for h in cancellation_histories if h.balance_before == initial_balance][0]
        assert first_history.amount == -initial_balance
        assert first_history.balance_after == 0.0
        
        # Должна быть хотя бы одна запись с положительной суммой - возврат на баланс
        positive_histories = [h for h in cancellation_histories if h.amount > 0]
        assert len(positive_histories) > 0

    def test_get_client_payments_with_cancelled_status(
        self,
        db_session: Session,
        test_client,
        test_admin
    ):
        """Тест получения списка платежей с фильтрацией по статусу отмены"""
        service = PaymentService(db_session)
        
        # Создаем обычный платеж
        payment1 = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Active payment",
            registered_by_id=test_admin.id
        )
        
        # Создаем платеж, который будет отменен
        payment2 = service.register_payment(
            client_id=test_client.id,
            amount=200.0,
            description="Payment to be cancelled",
            registered_by_id=test_admin.id
        )
        
        # Отменяем второй платеж
        cancelled_payment = service.cancel_payment(
            payment_id=payment2.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )
        
        # Получаем все платежи (должно быть 2)
        all_payments = service.get_client_payments(test_client.id)
        assert len(all_payments) == 2
        
        # Получаем только активные платежи (должен быть 1)
        active_payments = service.get_client_payments(
            client_id=test_client.id,
            cancelled_status="not_cancelled"
        )
        assert len(active_payments) == 1
        assert active_payments[0].id == payment1.id
        assert active_payments[0].cancelled_at is None
        
        # Получаем только отмененные платежи (должен быть 1)
        cancelled_payments = service.get_client_payments(
            client_id=test_client.id,
            cancelled_status="cancelled"
        )
        assert len(cancelled_payments) == 1
        assert cancelled_payments[0].id == payment2.id
        assert cancelled_payments[0].cancelled_at is not None
        
        # Проверяем ошибку при некорректном статусе
        with pytest.raises(HTTPException) as exc_info:
            service.get_client_payments(
                client_id=test_client.id,
                cancelled_status="invalid_status"
            )
        assert exc_info.value.status_code == 400
        assert "Invalid cancelled_status" in str(exc_info.value.detail)


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

    def test_create_payment_with_empty_description(self, client, auth_headers, payment_data):
        """Тест создания платежа с пустым описанием"""
        # Модифицируем данные платежа, устанавливая пустое описание
        modified_data = {**payment_data, "description": ""}
        
        # Отправляем запрос на создание платежа с пустым описанием
        response = client.post("/payments/", json=modified_data, headers=auth_headers)
        
        # Проверяем успешное создание
        assert response.status_code == 200
        assert response.json()["description"] == ""
        
        # Проверяем также с NULL значением (отсутствие поля)
        modified_data = {**payment_data}
        del modified_data["description"]
        response = client.post("/payments/", json=modified_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["description"] is None

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

    def test_get_client_payments_endpoint_filtering(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест эндпоинта получения списка платежей с фильтрацией по статусу отмены"""
        service = PaymentService(db_session)
        
        # Создаем обычный платеж
        payment1 = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Active payment",
            registered_by_id=test_admin.id
        )
        
        # Создаем платеж, который будет отменен
        payment2 = service.register_payment(
            client_id=test_client.id,
            amount=200.0,
            description="Payment to be cancelled",
            registered_by_id=test_admin.id
        )
        
        # Отменяем второй платеж
        cancelled_payment = service.cancel_payment(
            payment_id=payment2.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )
        
        # Получаем все платежи
        response = client.get(
            f"/payments/client/{test_client.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
        
        # Получаем только активные платежи
        response = client.get(
            f"/payments/client/{test_client.id}?cancelled_status=not_cancelled",
            headers=auth_headers
        )
        assert response.status_code == 200
        active_payments = response.json()
        assert len(active_payments) == 1
        assert active_payments[0]["cancelled_at"] is None
        
        # Получаем только отмененные платежи
        response = client.get(
            f"/payments/client/{test_client.id}?cancelled_status=cancelled",
            headers=auth_headers
        )
        assert response.status_code == 200
        cancelled_payments = response.json()
        assert len(cancelled_payments) == 1
        assert cancelled_payments[0]["cancelled_at"] is not None
        
        # Проверяем ошибку при некорректном статусе
        response = client.get(
            f"/payments/client/{test_client.id}?cancelled_status=invalid",
            headers=auth_headers
        )
        assert response.status_code == 400

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

    def test_get_payment_history_endpoint(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест эндпоинта получения истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем несколько платежей для создания истории
        for i in range(3):
            service.register_payment(
                client_id=test_client.id,
                amount=100.0 + i * 50,
                description=f"Test payment {i+1}",
                registered_by_id=test_admin.id
            )
        
        # Отменяем один платеж для создания записи отмены
        payments = service.get_client_payments(test_client.id)
        service.cancel_payment(
            payment_id=payments[0].id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )
        
        # Тестируем базовый запрос без фильтров
        response = client.post(
            "/payments/history",
            json={
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data
        assert len(data["items"]) > 0
        assert data["total"] > 0

    def test_get_payment_history_with_filters(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест фильтрации истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем платежи с разными суммами
        service.register_payment(
            client_id=test_client.id,
            amount=50.0,
            description="Small payment",
            registered_by_id=test_admin.id
        )
        
        service.register_payment(
            client_id=test_client.id,
            amount=200.0,
            description="Large payment",
            registered_by_id=test_admin.id
        )
        
        # Тестируем фильтр по минимальной сумме
        response = client.post(
            "/payments/history",
            json={
                "amount_min": 100.0,
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        
        # Проверяем, что все суммы >= 100
        for item in data["items"]:
            assert item["amount"] >= 100.0

    def test_get_payment_history_by_operation_type(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест фильтрации по типу операции"""
        service = PaymentService(db_session)
        
        # Создаем платеж
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_admin.id
        )
        
        # Отменяем платеж
        service.cancel_payment(
            payment_id=payment.id,
            cancelled_by_id=test_admin.id,
            cancellation_reason="Test cancellation"
        )
        
        # Тестируем фильтр по типу операции PAYMENT
        response = client.post(
            "/payments/history",
            json={
                "operation_type": "PAYMENT",
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        
        # Проверяем, что все записи имеют тип PAYMENT
        for item in data["items"]:
            assert item["operation_type"] == "PAYMENT"
        
        # Тестируем фильтр по типу операции CANCELLATION
        response = client.post(
            "/payments/history",
            json={
                "operation_type": "CANCELLATION",
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        
        # Проверяем, что все записи имеют тип CANCELLATION
        for item in data["items"]:
            assert item["operation_type"] == "CANCELLATION"

    def test_get_payment_history_by_client(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест фильтрации по клиенту"""
        service = PaymentService(db_session)
        
        # Создаем платеж для тестового клиента
        service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_admin.id
        )
        
        # Тестируем фильтр по клиенту
        response = client.post(
            "/payments/history",
            json={
                "client_id": test_client.id,
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        
        # Проверяем, что все записи принадлежат указанному клиенту
        for item in data["items"]:
            assert item["client_id"] == test_client.id

    def test_get_payment_history_pagination(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест пагинации истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем несколько платежей
        for i in range(5):
            service.register_payment(
                client_id=test_client.id,
                amount=100.0,
                description=f"Test payment {i+1}",
                registered_by_id=test_admin.id
            )
        
        # Тестируем первую страницу
        response = client.post(
            "/payments/history",
            json={
                "skip": 0,
                "limit": 2
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2
        assert data["has_more"] == True
        
        # Тестируем вторую страницу
        response = client.post(
            "/payments/history",
            json={
                "skip": 2,
                "limit": 2
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    def test_get_payment_history_validation_errors(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест валидации параметров истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем платеж
        service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_admin.id
        )
        
        # Тестируем ошибку при превышении лимита
        response = client.post(
            "/payments/history",
            json={
                "skip": 0,
                "limit": 1001  # Превышает максимальный лимит
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Limit cannot exceed 1000" in response.json()["detail"]
        
        # Тестируем ошибку при отрицательном skip
        response = client.post(
            "/payments/history",
            json={
                "skip": -1,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Skip cannot be negative" in response.json()["detail"]
        
        # Тестируем ошибку при некорректном диапазоне сумм
        response = client.post(
            "/payments/history",
            json={
                "amount_min": 200.0,
                "amount_max": 100.0,  # Мин больше макс
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Minimum amount cannot be greater than maximum amount" in response.json()["detail"]

    def test_get_payment_history_access_control(
        self,
        client,
        auth_headers,
        test_client,
        test_trainer,
        db_session
    ):
        """Тест контроля доступа к истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем платеж
        service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment",
            registered_by_id=test_trainer.id
        )
        
        # Тестируем доступ тренера (должен быть запрещен)
        # Сначала нужно создать токен для тренера
        from app.auth.jwt_handler import create_access_token
        
        trainer_token = create_access_token(
            data={
                "id": test_trainer.id,
                "email": test_trainer.email,
                "role": test_trainer.role.value
            }
        )
        
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        response = client.post(
            "/payments/history",
            json={
                "skip": 0,
                "limit": 10
            },
            headers=trainer_headers
        )
        
        # Тренер не должен иметь доступ к истории платежей
        assert response.status_code == 403
        assert "Only admins can view payment history" in response.json()["detail"]

    def test_get_payment_history_extended_data(
        self,
        client,
        auth_headers,
        test_client,
        test_admin,
        db_session
    ):
        """Тест получения расширенных данных в истории платежей"""
        service = PaymentService(db_session)
        
        # Создаем платеж
        payment = service.register_payment(
            client_id=test_client.id,
            amount=100.0,
            description="Test payment with extended data",
            registered_by_id=test_admin.id
        )
        
        # Получаем историю
        response = client.post(
            "/payments/history",
            json={
                "skip": 0,
                "limit": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        
        # Проверяем наличие расширенных данных
        item = data["items"][0]
        assert "client_first_name" in item
        assert "client_last_name" in item
        assert "created_by_first_name" in item
        assert "created_by_last_name" in item
        assert "payment_description" in item
        
        # Проверяем корректность данных
        assert item["client_first_name"] == test_client.first_name
        assert item["client_last_name"] == test_client.last_name
        assert item["created_by_first_name"] == test_admin.first_name
        assert item["created_by_last_name"] == test_admin.last_name 