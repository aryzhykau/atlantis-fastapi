import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.main import app
from app.models.user import User
from app.models.payment_history import PaymentHistory, OperationType
from app.schemas.user import UserRole
from app.auth.jwt_handler import create_access_token

client = TestClient(app)


@pytest.fixture
def test_admin(db_session: Session):
    """Создает тестового администратора для тестов"""
    user = User(
        email="admin@test.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        date_of_birth=date(1980, 1, 1),
        phone="1234567890"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user








@pytest.fixture
def payment_history_records(db_session: Session, test_trainer: User, test_client: User):
    """Создает записи истории платежей для тестов"""
    records = []
    for i in range(5):
        record = PaymentHistory(
            client_id=test_client.id,
            payment_id=None,
            invoice_id=None,
            operation_type=OperationType.PAYMENT,
            amount=Decimal(f"100.{i}"),
            balance_before=Decimal("1000.0"),
            balance_after=Decimal(f"1100.{i}"),
            description=f"Test payment {i}",
            created_at=datetime.now() - timedelta(days=i),
            created_by_id=test_trainer.id
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    for record in records:
        db_session.refresh(record)
    return records


class TestTrainerPaymentsEndpoint:
    """Тесты для эндпоинта получения платежей тренера"""
    
    def test_get_trainer_payments_success(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест успешного получения платежей тренера"""
        response = client.get(f"/trainers/{test_trainer.id}/payments", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data
        
        assert len(data["items"]) == 5
        assert data["total"] == 5
        assert data["skip"] == 0
        assert data["limit"] == 50
        assert data["has_more"] == False
        
        # Проверяем структуру первой записи
        first_item = data["items"][0]
        assert "id" in first_item
        assert "client_id" in first_item
        assert "operation_type" in first_item
        assert "amount" in first_item
        assert "description" in first_item
        assert "created_at" in first_item
        assert "created_by_id" in first_item
        assert first_item["created_by_id"] == test_trainer.id
    
    def test_get_trainer_payments_unauthorized(self, client, test_trainer: User):
        """Тест доступа без авторизации"""
        response = client.get(f"/trainers/{test_trainer.id}/payments")
        assert response.status_code == 401
    
    def test_get_trainer_payments_forbidden(self, client, test_trainer: User):
        """Тест доступа тренера к платежам (должен быть запрещен)"""
        # Создаем токен для тренера
        trainer_token = create_access_token(data={"sub": test_trainer.email, "id": test_trainer.id, "role": test_trainer.role.value})
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        response = client.get(f"/trainers/{test_trainer.id}/payments", headers=trainer_headers)
        assert response.status_code == 403
    
    def test_get_trainer_payments_not_found(self, client, auth_headers):
        """Тест получения платежей несуществующего тренера"""
        response = client.get("/trainers/99999/payments", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_trainer_payments_with_filters(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест получения платежей с фильтрами"""
        # Тестируем фильтр по периоду
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?period=week",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0  # Должны быть записи за последнюю неделю
    
    def test_get_trainer_payments_with_amount_filter(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест фильтрации по сумме"""
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?amount_min=100.2&amount_max=100.4",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем, что все суммы в диапазоне
        for item in data["items"]:
            amount = float(item["amount"])
            assert 100.2 <= amount <= 100.4
    
    def test_get_trainer_payments_with_date_filter(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест фильтрации по дате"""
        # Фильтруем по последним 3 дням
        date_from = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?date_from={date_from}&date_to={date_to}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
    
    def test_get_trainer_payments_with_description_search(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест поиска по описанию"""
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?description_search=Test payment 1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем, что найдена запись с нужным описанием
        found = False
        for item in data["items"]:
            if "Test payment 1" in item["description"]:
                found = True
                break
        assert found
    
    def test_get_trainer_payments_pagination(self, client, auth_headers, test_trainer: User, payment_history_records):
        """Тест пагинации"""
        # Первая страница
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?skip=0&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2
        assert data["has_more"] == True
        
        # Вторая страница
        response = client.get(
            f"/trainers/{test_trainer.id}/payments?skip=2&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2
        assert data["has_more"] == True
    
    def test_get_trainer_payments_empty_result(self, client, auth_headers, db_session: Session):
        """Тест пустого результата"""
        # Создаем тренера без платежей
        empty_trainer = User(
            first_name="Пустой",
            last_name="Тренер",
            email="emptytrainer@example.com",
            phone="1234567892",
            date_of_birth=date(1991, 6, 15),
            role=UserRole.TRAINER,
            is_active=True,
        )
        db_session.add(empty_trainer)
        db_session.commit()
        db_session.refresh(empty_trainer)
        
        # Получаем платежи тренера (должно быть пусто)
        response = client.get(f"/trainers/{empty_trainer.id}/payments", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0
        assert data["has_more"] == False 