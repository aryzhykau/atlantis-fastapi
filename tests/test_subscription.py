import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import StudentSubscription, Invoice, InvoiceStatus
from app.services.subscription import SubscriptionService


@pytest.fixture
def subscription_data():
    return {
        "name": "Test Subscription",
        "price": 100.0,
        "number_of_sessions": 8,
        "validity_days": 30,
        "is_active": True
    }


@pytest.fixture
def student_subscription_data():
    return {
        "student_id": 1,
        "subscription_id": 1,
        "is_auto_renew": False
    }


class TestSubscriptionEndpoints:
    def test_create_subscription(self, client, auth_headers, subscription_data):
        response = client.post("/subscriptions/", json=subscription_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == subscription_data["name"]
        assert response.json()["price"] == subscription_data["price"]

    def test_get_subscriptions(self, client, auth_headers, subscription_data):
        client.post("/subscriptions/", json=subscription_data, headers=auth_headers)
        response = client.get("/subscriptions/", headers=auth_headers)
        assert response.status_code == 200
        subscriptions = response.json()["items"]
        assert len(subscriptions) == 1
        assert subscriptions[0]["name"] == subscription_data["name"]

    def test_get_subscription_by_id(self, client, auth_headers, subscription_data):
        create_response = client.post("/subscriptions/", json=subscription_data, headers=auth_headers)
        subscription_id = create_response.json()["id"]
        
        response = client.get(f"/subscriptions/{subscription_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == subscription_id
        assert response.json()["name"] == subscription_data["name"]

    def test_update_subscription(self, client, auth_headers, subscription_data):
        create_response = client.post("/subscriptions/", json=subscription_data, headers=auth_headers)
        subscription_id = create_response.json()["id"]
        
        update_data = {"name": "Updated Subscription", "price": 150.0}
        response = client.patch(f"/subscriptions/{subscription_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == update_data["name"]
        assert response.json()["price"] == update_data["price"]


class TestStudentSubscription:
    def test_add_subscription_to_student(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = SubscriptionService(db_session)
        student_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )

        assert student_subscription.student_id == test_student.id
        assert student_subscription.subscription_id == test_subscription.id
        assert student_subscription.sessions_left == test_subscription.number_of_sessions
        assert student_subscription.transferred_sessions == 0
        assert not student_subscription.is_auto_renew

        # Проверяем создание инвойса
        invoice = db_session.query(Invoice).filter(
            Invoice.student_id == test_student.id,
            Invoice.subscription_id == test_subscription.id
        ).first()
        assert invoice is not None
        assert invoice.amount == test_subscription.price
        assert invoice.status == InvoiceStatus.UNPAID

    def test_auto_renewal_subscription(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = SubscriptionService(db_session)
        student_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=True,
            created_by_id=test_admin.id
        )

        # Обновляем статус автопродления
        updated_subscription = service.update_auto_renewal(
            student_subscription_id=student_subscription.id,
            is_auto_renew=True,
            updated_by_id=test_admin.id
        )
        assert updated_subscription.is_auto_renew

    def test_freeze_subscription(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = SubscriptionService(db_session)
        student_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )

        # Замораживаем абонемент
        freeze_days = 7
        freeze_start = datetime.now(timezone.utc)
        frozen_subscription = service.freeze_subscription(
            student_subscription_id=student_subscription.id,
            freeze_start_date=freeze_start,
            freeze_duration_days=freeze_days,
            updated_by_id=test_admin.id
        )

        assert frozen_subscription.freeze_start_date.replace(tzinfo=timezone.utc) == freeze_start
        assert frozen_subscription.freeze_end_date.replace(tzinfo=timezone.utc) == freeze_start + timedelta(days=freeze_days)

        # Размораживаем абонемент
        unfrozen_subscription = service.unfreeze_subscription(
            student_subscription_id=student_subscription.id,
            updated_by_id=test_admin.id
        )

        assert unfrozen_subscription.freeze_start_date is None
        assert unfrozen_subscription.freeze_end_date is None


    def test_subscription_expiration(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        service = SubscriptionService(db_session)
        student_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )

        # Устанавливаем дату окончания в прошлом
        student_subscription.end_date = datetime.utcnow() - timedelta(days=1)
        db_session.commit()

        # Проверяем, что абонемент считается истекшим
        assert student_subscription.status == "expired"

    def test_transfer_sessions_on_new_subscription(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        """Тест переноса тренировок при создании нового абонемента"""
        service = SubscriptionService(db_session)
        
        # Создаем первый абонемент
        old_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )
        
        # Устанавливаем дату окончания в прошлом и оставляем неиспользованные тренировки
        old_subscription.end_date = datetime.utcnow() - timedelta(days=1)
        old_subscription.sessions_left = 5  # Осталось 5 тренировок
        db_session.commit()
        
        # Создаем новый абонемент
        new_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )
        
        # Проверяем, что перенеслось не более 3 тренировок
        assert new_subscription.transferred_sessions == 3
        assert new_subscription.sessions_left == test_subscription.number_of_sessions + 3
        
        # Проверяем, что в старом абонементе тренировки обнулились
        db_session.refresh(old_subscription)
        assert old_subscription.sessions_left == 0
        assert old_subscription.transferred_sessions == 0

    def test_process_auto_renewals(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        """Тест процесса автопродления абонементов"""
        service = SubscriptionService(db_session)
        
        # Создаем абонемент с автопродлением, который скоро закончится
        subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=True,
            created_by_id=test_admin.id
        )
        
        # Устанавливаем дату окончания через 2 дня и оставляем неиспользованные тренировки
        subscription.end_date = datetime.utcnow()
        subscription.sessions_left = 5  # Осталось 5 тренировок
        db_session.commit()
        
        # Запускаем процесс автопродления
        renewed_subscriptions = service.process_auto_renewals(test_admin.id)
        
        assert len(renewed_subscriptions) == 1
        new_subscription = renewed_subscriptions[0]
        
        # Проверяем параметры нового абонемента
        assert new_subscription.student_id == test_student.id
        assert new_subscription.subscription_id == test_subscription.id
        assert new_subscription.start_date == subscription.end_date
        assert new_subscription.is_auto_renew == True
        assert new_subscription.transferred_sessions == 3  # Перенеслось 3 тренировки из 5
        assert new_subscription.sessions_left == test_subscription.number_of_sessions + 3
        
        # Проверяем, что у старого абонемента появился инвойс автопродления
        db_session.refresh(subscription)
        assert subscription.auto_renewal_invoice_id is not None
        
        # Проверяем инвойс автопродления
        invoice = db_session.query(Invoice).filter_by(id=subscription.auto_renewal_invoice_id).first()
        assert invoice is not None
        assert invoice.student_id == test_student.id
        assert invoice.subscription_id == test_subscription.id
        assert invoice.is_auto_renewal == True
        assert invoice.status == InvoiceStatus.UNPAID


