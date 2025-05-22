import pytest
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.models import Invoice, InvoiceStatus, InvoiceType, StudentSubscription, Student, Payment, RealTraining
from app.services.invoice import InvoiceService


@pytest.fixture
def invoice_data(test_student, test_subscription):
    return {
        "client_id": test_student.client_id,
        "student_id": test_student.id,
        "subscription_id": test_subscription.id,
        "amount": 100.0,
        "description": "Test invoice",
        "is_auto_renewal": False
    }


@pytest.fixture
def training_invoice_data(test_student, test_training):
    return {
        "client_id": test_student.client_id,
        "student_id": test_student.id,
        "training_id": test_training.id,
        "amount": 100.0,
        "description": "Test training invoice",
        "is_auto_renewal": False
    }


class TestInvoiceService:
    def test_create_subscription_invoice(
        self,
        db_session: Session,
        test_client,
        test_student,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        invoice = service.create_subscription_invoice(
            client_id=test_client.id,
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            amount=test_subscription.price,
            description="Test subscription invoice",
            created_by_id=test_admin.id,
            is_auto_renewal=False
        )

        assert invoice.client_id == test_client.id
        assert invoice.student_id == test_student.id
        assert invoice.subscription_id == test_subscription.id
        assert invoice.type == InvoiceType.SUBSCRIPTION
        assert invoice.amount == test_subscription.price
        assert invoice.status == InvoiceStatus.UNPAID
        assert not invoice.is_auto_renewal

    def test_create_training_invoice(
        self,
        db_session: Session,
        test_client,
        test_student,
        test_admin
    ):
        service = InvoiceService(db_session)
        
        # Создаем тестовую тренировку
        training = RealTraining(
            training_date=date.today(),
            start_time=datetime.now().time(),
            responsible_trainer_id=test_admin.id,
            training_type_id=1
        )
        db_session.add(training)
        db_session.flush()
        
        # Создаем инвойс для разовой тренировки
        invoice = service.create_training_invoice(
            client_id=test_client.id,
            student_id=test_student.id,
            training_id=training.id,
            amount=50.0,
            description="Test training invoice",
            created_by_id=test_admin.id
        )

        assert invoice.client_id == test_client.id
        assert invoice.student_id == test_student.id
        assert invoice.training_id == training.id
        assert invoice.subscription_id is None  # Для разовой тренировки не нужен абонемент
        assert invoice.type == InvoiceType.TRAINING
        assert invoice.amount == 50.0
        assert invoice.status == InvoiceStatus.UNPAID

    def test_cancel_invoice(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        invoice = service.create_subscription_invoice(
            client_id=test_student.client_id,
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            amount=test_subscription.price,
            description="Test subscription invoice",
            created_by_id=test_admin.id
        )

        cancelled_invoice = service.cancel_invoice(
            invoice_id=invoice.id,
            cancelled_by_id=test_admin.id
        )

        assert cancelled_invoice.status == InvoiceStatus.CANCELLED
        assert cancelled_invoice.cancelled_at is not None
        assert cancelled_invoice.cancelled_by_id == test_admin.id

    def test_process_payment(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin,
        test_payment
    ):
        service = InvoiceService(db_session)
        
        # Создаем два неоплаченных инвойса
        invoice1 = service.create_subscription_invoice(
            client_id=test_student.client_id,
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            amount=50.0,
            description="Test invoice 1",
            created_by_id=test_admin.id
        )

        invoice2 = service.create_subscription_invoice(
            client_id=test_student.client_id,
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            amount=30.0,
            description="Test invoice 2",
            created_by_id=test_admin.id
        )

        # Обрабатываем платеж на сумму, достаточную для погашения обоих инвойсов
        test_payment.amount = 100.0
        paid_invoices = service.process_payment(test_payment, test_student.id)

        assert len(paid_invoices) == 2
        for invoice in paid_invoices:
            assert invoice.status == InvoiceStatus.PAID
            assert invoice.paid_at is not None
            assert invoice.payment_id == test_payment.id

    def test_revert_payment(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin,
        test_payment
    ):
        service = InvoiceService(db_session)

        # Создаем и оплачиваем инвойс
        invoice = service.create_subscription_invoice(
            client_id=test_student.client_id,
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            amount=test_payment.amount,
            description="Test invoice",
            created_by_id=test_admin.id
        )

        # Оплачиваем инвойс
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        invoice.payment_id = test_payment.id
        db_session.commit()

        # Отменяем платеж
        service.revert_payment(invoice.id, test_admin.id)

        # Проверяем, что инвойс снова неоплачен
        assert invoice.status == InvoiceStatus.UNPAID
        assert invoice.paid_at is None
        assert invoice.payment_id is None

    def test_create_auto_renewal_invoice(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        
        # Создаем подписку студента с автопродлением
        student_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            is_auto_renew=True,
            sessions_left=0,
            transferred_sessions=0
        )
        db_session.add(student_subscription)
        db_session.commit()

        # Создаем инвойс для автопродления
        auto_renewal_invoice = service.create_auto_renewal_invoice(
            student_subscription=student_subscription,
            created_by_id=test_admin.id
        )

        assert auto_renewal_invoice.student_id == test_student.id
        assert auto_renewal_invoice.subscription_id == test_subscription.id
        assert auto_renewal_invoice.type == InvoiceType.SUBSCRIPTION
        assert auto_renewal_invoice.amount == test_subscription.price
        assert auto_renewal_invoice.is_auto_renewal
        assert "Auto-renewal" in auto_renewal_invoice.description

    def test_auto_pay_invoices(
        self,
        db_session: Session,
        test_client,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        
        # Создаем несколько неоплаченных инвойсов
        invoice1 = service.create_subscription_invoice(
            client_id=test_client.id,
            subscription_id=test_subscription.id,
            amount=50.0,
            description="Test invoice 1",
            created_by_id=test_admin.id
        )
        
        invoice2 = service.create_subscription_invoice(
            client_id=test_client.id,
            subscription_id=test_subscription.id,
            amount=30.0,
            description="Test invoice 2",
            created_by_id=test_admin.id
        )
        
        # Устанавливаем баланс клиента
        test_client.balance = 100.0
        db_session.commit()
        
        # Пробуем оплатить инвойсы
        paid_invoices = service.auto_pay_invoices(
            client_id=test_client.id,
            available_amount=90.0
        )
        
        # Проверяем результаты
        assert len(paid_invoices) == 2
        assert paid_invoices[0].status == InvoiceStatus.PAID
        assert paid_invoices[1].status == InvoiceStatus.PAID
        assert test_client.balance == 20.0  # 100 - 50 - 30
        
        # Проверяем, что платежи созданы
        payments = db_session.query(Payment).all()
        assert len(payments) == 2
        assert payments[0].amount == 50.0
        assert payments[1].amount == 30.0
        
        # Проверяем связь инвойсов с платежами
        assert paid_invoices[0].payment_id == payments[0].id
        assert paid_invoices[1].payment_id == payments[1].id

    def test_auto_pay_invoices_partial(
        self,
        db_session: Session,
        test_client,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        
        # Создаем несколько неоплаченных инвойсов
        invoice1 = service.create_subscription_invoice(
            client_id=test_client.id,
            subscription_id=test_subscription.id,
            amount=50.0,
            description="Test invoice 1",
            created_by_id=test_admin.id
        )
        
        invoice2 = service.create_subscription_invoice(
            client_id=test_client.id,
            subscription_id=test_subscription.id,
            amount=30.0,
            description="Test invoice 2",
            created_by_id=test_admin.id
        )
        
        # Устанавливаем баланс клиента
        test_client.balance = 60.0
        db_session.commit()
        
        # Пробуем оплатить инвойсы
        paid_invoices = service.auto_pay_invoices(test_client.id, 50.0)
        
        # Проверяем результаты
        assert len(paid_invoices) == 1
        assert paid_invoices[0].id == invoice1.id
        assert paid_invoices[0].status == InvoiceStatus.PAID
        assert invoice2.status == InvoiceStatus.UNPAID
        assert test_client.balance == 10.0  # 60 - 50 = 10

    def test_get_client_invoices(
        self,
        db_session: Session,
        test_client,
        test_subscription,
        test_admin
    ):
        service = InvoiceService(db_session)
        
        # Создаем несколько инвойсов для клиента
        for i in range(3):
            service.create_subscription_invoice(
                client_id=test_client.id,
                subscription_id=test_subscription.id,
                amount=100.0,
                description=f"Test invoice {i+1}",
                created_by_id=test_admin.id
            )
            
        # Получаем список инвойсов
        invoices = service.get_client_invoices(test_client.id)
        
        assert len(invoices) == 3
        for invoice in invoices:
            assert invoice.client_id == test_client.id
            assert invoice.status == InvoiceStatus.UNPAID


class TestInvoiceEndpoints:
    def test_get_invoice(self, client, auth_headers, test_invoice):
        response = client.get(f"/invoices/{test_invoice.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == test_invoice.id
        assert response.json()["amount"] == test_invoice.amount

    def test_get_student_invoices(
        self,
        client,
        auth_headers,
        test_student,
        test_subscription,
        test_admin,
        db_session
    ):
        service = InvoiceService(db_session)
        
        # Создаем несколько инвойсов для студента
        for i in range(3):
            service.create_subscription_invoice(
                client_id=test_student.client_id,
                student_id=test_student.id,
                subscription_id=test_subscription.id,
                amount=100.0,
                description=f"Test invoice {i+1}",
                created_by_id=test_admin.id
            )

        response = client.get(
            f"/invoices/student/{test_student.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        invoices = response.json()["items"]
        assert len(invoices) == 3

    def test_get_client_invoices(
        self,
        client,
        auth_headers,
        test_client,
        test_subscription,
        test_admin,
        db_session
    ):
        service = InvoiceService(db_session)
        
        # Создаем несколько инвойсов для клиента
        for i in range(3):
            service.create_subscription_invoice(
                client_id=test_client.id,
                subscription_id=test_subscription.id,
                amount=100.0,
                description=f"Test invoice {i+1}",
                created_by_id=test_admin.id
            )

        response = client.get(
            f"/invoices/client/{test_client.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        invoices = response.json()["items"]
        assert len(invoices) == 3
        
        # Проверяем фильтрацию по статусу
        response = client.get(
            f"/invoices/client/{test_client.id}?status=UNPAID",
            headers=auth_headers
        )
        assert response.status_code == 200
        invoices = response.json()["items"]
        assert len(invoices) == 3
        for invoice in invoices:
            assert invoice["client_id"] == test_client.id
            assert invoice["status"] == "UNPAID"

    def test_create_subscription_invoice_endpoint(
        self,
        client,
        auth_headers,
        invoice_data
    ):
        response = client.post(
            "/invoices/subscription",
            json=invoice_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["amount"] == invoice_data["amount"]
        assert response.json()["type"] == InvoiceType.SUBSCRIPTION

    def test_create_training_invoice_endpoint(
        self,
        client,
        auth_headers,
        training_invoice_data
    ):
        response = client.post(
            "/invoices/training",
            json=training_invoice_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["amount"] == training_invoice_data["amount"]
        assert response.json()["type"] == InvoiceType.TRAINING

    def test_cancel_invoice_endpoint(
        self,
        client,
        auth_headers,
        test_invoice
    ):
        response = client.post(
            f"/invoices/{test_invoice.id}/cancel",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == InvoiceStatus.CANCELLED 