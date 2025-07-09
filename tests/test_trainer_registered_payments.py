import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

from app.main import app
from app.models import User, Payment, UserRole
from app.crud.trainer import create_trainer
from app.schemas.user import TrainerCreate
from app.auth.jwt_handler import create_access_token

# Убираем создание клиента здесь, будем использовать фикстуру из conftest





def test_get_trainer_registered_payments_success(client, db_session: Session, test_trainer, test_client, auth_headers):
    """Тест успешного получения платежей тренера"""
    # Создаем платеж
    payment = Payment(
        client_id=test_client.id,
        amount=500.0,
        description="Test payment",
        registered_by_id=test_trainer.id,
        payment_date=datetime.utcnow()
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Запрашиваем платежи тренера
    response = client.get(
        f"/trainers/{test_trainer.id}/registered-payments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "payments" in data
    assert len(data["payments"]) == 1
    assert data["payments"][0]["id"] == payment.id
    assert data["payments"][0]["amount"] == 500.0
    assert data["payments"][0]["client_id"] == test_client.id
    assert data["payments"][0]["description"] == "Test payment"
    assert data["total"] == 1


def test_get_trainer_registered_payments_empty(client, db_session: Session, test_trainer, auth_headers):
    """Тест получения платежей тренера без платежей"""
    response = client.get(
        f"/trainers/{test_trainer.id}/registered-payments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "payments" in data
    assert len(data["payments"]) == 0
    assert data["total"] == 0


def test_get_trainer_registered_payments_with_filters(client, db_session: Session, test_trainer, test_client, auth_headers):
    """Тест получения платежей тренера с фильтрами"""
    # Создаем несколько платежей
    payment1 = Payment(
        client_id=test_client.id,
        amount=100.0,
        description="Small payment",
        registered_by_id=test_trainer.id,
        payment_date=datetime.utcnow()
    )
    payment2 = Payment(
        client_id=test_client.id,
        amount=500.0,
        description="Large payment",
        registered_by_id=test_trainer.id,
        payment_date=datetime.utcnow()
    )
    db_session.add_all([payment1, payment2])
    db_session.commit()
    
    # Фильтруем по сумме
    response = client.get(
        f"/trainers/{test_trainer.id}/registered-payments?amount_min=200",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["payments"]) == 1
    assert data["payments"][0]["amount"] == 500.0


def test_get_trainer_registered_payments_unauthorized(client, db_session: Session, test_trainer):
    """Тест доступа без авторизации"""
    response = client.get(f"/trainers/{test_trainer.id}/registered-payments")
    assert response.status_code == 401


def test_get_trainer_registered_payments_trainer_access(client, db_session: Session, test_trainer, test_client):
    """Тест доступа тренера к своим платежам"""
    # Создаем токен для тренера
    token = create_access_token({"id": test_trainer.id, "role": test_trainer.role.value})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Создаем платеж
    payment = Payment(
        client_id=test_client.id,
        amount=300.0,
        description="Trainer payment",
        registered_by_id=test_trainer.id,
        payment_date=datetime.utcnow()
    )
    db_session.add(payment)
    db_session.commit()
    
    # Тренер может смотреть свои платежи
    response = client.get(
        f"/trainers/{test_trainer.id}/registered-payments",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["payments"]) == 1
    assert data["payments"][0]["amount"] == 300.0


def test_get_trainer_registered_payments_other_trainer_denied(client, db_session: Session, test_trainer, test_client):
    """Тест запрета тренеру смотреть чужие платежи"""
    # Создаем второго тренера
    other_trainer = User(
        first_name="Other",
        last_name="Trainer",
        email="other@test.com",
        phone="+1234567893",
        date_of_birth=date(1995, 3, 20),
        role=UserRole.TRAINER
    )
    db_session.add(other_trainer)
    db_session.commit()
    
    # Создаем токен для второго тренера
    token = create_access_token({"id": other_trainer.id, "role": other_trainer.role.value})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Второй тренер не может смотреть платежи первого
    response = client.get(
        f"/trainers/{test_trainer.id}/registered-payments",
        headers=headers
    )
    
    assert response.status_code == 403 