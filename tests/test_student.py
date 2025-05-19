import pytest
from datetime import datetime, date
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Student, User, UserRole, Subscription, RealTrainingStudent, TrainingType
from app.crud.student import get_student_by_id, get_students, get_students_by_client_id

student = {
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "2015-04-21",
    "client_id": 2,
}

def test_create_student(client, auth_headers, create_test_client): 
    response = client.post("/students/", json=student, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "string"

def test_create_student_with_future_date(client, auth_headers, create_test_client):
    """Тест создания студента с датой рождения в будущем"""
    invalid_student = student.copy()
    invalid_student["date_of_birth"] = "2050-01-01"
    
    response = client.post("/students/", json=invalid_student, headers=auth_headers)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("Дата рождения не может быть в будущем" in error["msg"] for error in errors)

def test_create_student_with_invalid_client(client, auth_headers):
    """Тест создания студента с несуществующим клиентом"""
    invalid_student = student.copy()
    invalid_student["client_id"] = 99999
    
    response = client.post("/students/", json=invalid_student, headers=auth_headers)
    assert response.status_code == 400
    assert "клиент" in response.json()["detail"].lower()

def test_get_student(client, auth_headers, create_test_client):
    """Тест получения студента по ID"""
    # Создаем студента
    student_data = student.copy()
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Получаем студента
    response = client.get(f"/students/{student_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == student_id
    assert response.json()["first_name"] == student["first_name"]

def test_get_students_by_client(client, auth_headers, create_test_client):
    """Тест получения списка студентов клиента"""
    # Создаем двух студентов для одного клиента
    client.post("/students/", json=student, headers=auth_headers)
    client.post("/students/", json=student, headers=auth_headers)
    
    # Получаем список студентов клиента
    response = client.get(f"/students/client/{create_test_client.id}", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_update_student(client, auth_headers, create_test_client):
    """Тест обновления информации о студенте"""
    # Создаем студента
    student_data = student.copy()
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Обновляем информацию
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    response = client.patch(f"/students/{student_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["last_name"] == "Name"

def test_update_student_with_invalid_data(client, auth_headers, create_test_client):
    """Тест обновления студента с некорректными данными"""
    # Создаем студента
    student_data = student.copy()
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Пытаемся обновить с некорректной датой рождения
    update_data = {
        "date_of_birth": "2050-01-01"
    }
    response = client.patch(f"/students/{student_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("Дата рождения не может быть в будущем" in error["msg"] for error in errors)

def test_deactivate_student(client, auth_headers, create_test_client):
    """Тест деактивации отдельного студента."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Деактивируем студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == False
    assert response.json()["deactivation_date"] is not None
    assert response.json()["client_status"] == True  # Клиент остается активным

def test_reactivate_student_with_active_client(client, auth_headers, create_test_client):
    """Тест реактивации студента с активным клиентом."""
    # Создаем и деактивируем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    client.patch(f"/students/{student_id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Реактивируем студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": True}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    assert response.json()["deactivation_date"] is None
    assert response.json()["client_status"] == True

def test_reactivate_student_with_inactive_client(client, auth_headers, create_test_client):
    """Тест реактивации студента с неактивным клиентом."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Сначала деактивируем студента
    client.patch(f"/students/{student_id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Деактивируем клиента
    client.patch(f"/clients/{create_test_client.id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Пытаемся реактивировать студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": True}, 
                          headers=auth_headers)
    
    assert response.status_code == 400
    assert "родительский клиент неактивен" in response.json()["detail"]

def test_deactivate_nonexistent_student(client, auth_headers):
    """Тест деактивации несуществующего студента."""
    response = client.patch("/students/99999/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    assert response.status_code == 404

def test_deactivate_student_without_auth(client, create_test_client):
    """Тест деактивации студента без авторизации."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", 
                                json=student_data, 
                                headers={"Authorization": "Bearer dev_token"})
    student_id = create_response.json()["id"]
    
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": False})
    assert response.status_code == 401

def test_student_subscription_relationship(client, auth_headers, create_test_client, db_session: Session):
    """Тест связи студента с абонементами"""
    # Создаем студента
    create_response = client.post("/students/", json=student, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Получаем студента из базы
    db_student = get_student_by_id(db_session, student_id)
    assert db_student is not None
    
    # Проверяем, что у нового студента нет абонементов
    assert len(db_student.subscriptions) == 0
    assert db_student.active_subscription_id is None

def test_student_real_trainings_relationship(client, auth_headers, create_test_client, db_session: Session):
    """Тест связи студента с реальными тренировками"""
    # Создаем студента
    create_response = client.post("/students/", json=student, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Получаем студента из базы
    db_student = get_student_by_id(db_session, student_id)
    assert db_student is not None
    
    # Проверяем, что у нового студента нет тренировок
    assert len(db_student.real_trainings) == 0

def test_student_payment_history_relationship(client, auth_headers, create_test_client, db_session: Session):
    """Тест связи студента с историей платежей"""
    # Создаем студента
    create_response = client.post("/students/", json=student, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Создаем платеж для клиента
    payment_data = {
        "client_id": create_test_client.id,
        "amount": 100.0,
        "description": "Test payment for student"
    }
    payment_response = client.post("/payments/", json=payment_data, headers=auth_headers)
    assert payment_response.status_code == 200
    
    # Проверяем, что платеж отображается в истории студента
    response = client.get(f"/students/{student_id}/payments", headers=auth_headers)
    assert response.status_code == 200
    payments = response.json()
    assert len(payments) > 0
    assert any(p["amount"] == 100.0 for p in payments)

def test_student_access_restrictions(client, auth_headers, create_test_client):
    """Тест ограничений доступа к данным студента"""
    # Создаем студента
    create_response = client.post("/students/", json=student, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Пытаемся получить данные студента без авторизации
    response = client.get(f"/students/{student_id}")
    assert response.status_code == 401
    
    # Создаем нового клиента с другим ID
    other_client_data = {
        "first_name": "Other",
        "last_name": "Client",
        "email": "other@test.com",
        "phone": "9876543210",
        "date_of_birth": "1990-01-01",
        "whatsapp_number": "9876543210",
        "balance": 0,
        "is_student": False,
        "students": None
    }
    other_client_response = client.post("/clients/", json=other_client_data, headers=auth_headers)
    other_client_id = other_client_response.json()["id"]
    
    # Создаем токен для другого клиента
    from app.auth.jwt_handler import create_access_token
    other_client_token = create_access_token(
        data={"sub": "other@test.com", "id": other_client_id, "role": "CLIENT"}
    )
    
    # Пытаемся получить данные студента от имени другого клиента
    other_headers = {"Authorization": f"Bearer {other_client_token}"}
    response = client.get(f"/students/{student_id}", headers=other_headers)
    assert response.status_code == 403

def test_student_cascade_operations(client, auth_headers, create_test_client, db_session: Session):
    """Тест поведения при удалении связанных сущностей"""
    # Создаем студента
    create_response = client.post("/students/", json=student, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Создаем тип тренировки
    training_type = TrainingType(
        name="Test Training",
        is_subscription_only=False,
        price=100.0,
        color="#FF0000",
        is_active=True
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    
    # Создаем тренера
    trainer = User(
        first_name="Test",
        last_name="Trainer",
        email="trainer@test.com",
        phone="9999999999",  # Уникальный номер телефона
        date_of_birth=date(1990, 1, 1),
        role=UserRole.TRAINER,
        is_authenticated_with_google=True
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    
    # Создаем тренировку
    training_data = {
        "training_date": "2024-03-20",
        "start_time": "10:00",
        "responsible_trainer_id": trainer.id,
        "training_type_id": training_type.id
    }
    training_response = client.post("/real-trainings/", json=training_data, headers=auth_headers)
    assert training_response.status_code == 201
    training_id = training_response.json()["id"]
    
    # Добавляем студента на тренировку
    student_training_data = {
        "student_id": student_id
    }
    student_training_response = client.post(
        f"/real-trainings/{training_id}/students",
        json=student_training_data,
        headers=auth_headers
    )
    assert student_training_response.status_code == 200

def test_deactivate_student_full_scenario(client, auth_headers, create_test_client, db_session: Session):
    """Тест полного сценария деактивации студента:
    1. Создание студента и добавление его на тренировку
    2. Деактивация студента
    3. Проверка, что нельзя добавить деактивированного студента на новую тренировку
    """
    # 1. Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Создаем тип тренировки
    training_type = TrainingType(
        name="Test Training",
        is_subscription_only=False,
        price=100.0,
        color="#FF0000",
        is_active=True
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    
    # Создаем тренера
    trainer = User(
        first_name="Test",
        last_name="Trainer",
        email="trainer@test.com",
        phone="9999999999",  # Уникальный номер телефона
        date_of_birth=date(1990, 1, 1),
        role=UserRole.TRAINER,
        is_authenticated_with_google=True
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    
    # Создаем первую тренировку и добавляем студента
    training_data = {
        "training_date": "2024-03-20",
        "start_time": "10:00",
        "responsible_trainer_id": trainer.id,
        "training_type_id": training_type.id
    }
    training_response = client.post("/real-trainings/", json=training_data, headers=auth_headers)
    assert training_response.status_code == 201
    training_id = training_response.json()["id"]
    
    # Добавляем студента на тренировку
    student_training_data = {
        "student_id": student_id
    }
    student_training_response = client.post(
        f"/real-trainings/{training_id}/students",
        json=student_training_data,
        headers=auth_headers
    )
    assert student_training_response.status_code == 200
    
    # 2. Деактивируем студента
    deactivate_response = client.patch(
        f"/students/{student_id}/status",
        json={"is_active": False},
        headers=auth_headers
    )
    assert deactivate_response.status_code == 200
    assert not deactivate_response.json()["is_active"]
    
    # 3. Пытаемся добавить деактивированного студента на новую тренировку
    new_training_data = {
        "training_date": "2024-03-21",
        "start_time": "11:00",
        "responsible_trainer_id": trainer.id,
        "training_type_id": training_type.id
    }
    new_training_response = client.post("/real-trainings/", json=new_training_data, headers=auth_headers)
    assert new_training_response.status_code == 201
    new_training_id = new_training_response.json()["id"]
    
    student_training_data = {
        "student_id": student_id
    }
    error_response = client.post(
        f"/real-trainings/{new_training_id}/students",
        json=student_training_data,
        headers=auth_headers
    )
    assert error_response.status_code == 400
    assert "inactive" in error_response.json()["detail"].lower()

