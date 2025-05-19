from datetime import date, time, datetime, timedelta
import pytest
from fastapi import status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    TrainingTemplate,
    TrainingType,
    User,
    Student,
    TrainingStudentTemplate,
    RealTraining,
    RealTrainingStudent,
)
from app.models.user import UserRole
from app.crud.real_training import generate_next_week_trainings


@pytest.fixture
def training_type(db_session: Session):
    """Создает тестовый тип тренировки"""
    training_type = TrainingType(
        name="Test Training",
        color="#FF0000",
        is_subscription_only=False,
        is_active=True
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    yield training_type
    # Удаляем тип тренировки после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM real_trainings"))
    db_session.execute(text("DELETE FROM training_client_templates"))
    db_session.execute(text("DELETE FROM training_templates"))
    db_session.execute(text("DELETE FROM training_types"))
    db_session.commit()


@pytest.fixture
def trainer(db_session: Session):
    """Создает тестового тренера"""
    trainer = User(
        first_name="Test",
        last_name="Trainer",
        date_of_birth=date(1990, 1, 1),
        email="trainer@test.com",
        phone="1234567890",
        role=UserRole.TRAINER,
        is_active=True
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    yield trainer
    # Удаляем тренера после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM real_trainings"))
    db_session.execute(text("DELETE FROM training_client_templates"))
    db_session.execute(text("DELETE FROM training_templates"))
    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": trainer.id})
    db_session.commit()


@pytest.fixture
def student(db_session: Session, create_test_client):
    """Создает тестового студента"""
    student = Student(
        first_name="Test",
        last_name="Student",
        date_of_birth=date(2000, 1, 1),
        is_active=True,
        client_id=create_test_client.id
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    yield student
    # Удаляем студента после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM training_client_templates"))
    db_session.execute(text("DELETE FROM students WHERE id = :id"), {"id": student.id})
    db_session.commit()


@pytest.fixture
def training_template(db_session: Session, training_type, trainer):
    """Создает тестовый шаблон тренировки"""
    template = TrainingTemplate(
        day_number=1,  # Понедельник
        start_time=time(10, 0),  # 10:00
        responsible_trainer_id=trainer.id,
        training_type_id=training_type.id
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    yield template
    # Удаляем шаблон после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM real_trainings"))
    db_session.execute(text("DELETE FROM training_client_templates"))
    db_session.execute(text("DELETE FROM training_templates WHERE id = :id"), {"id": template.id})
    db_session.commit()


@pytest.fixture
def template_with_student(db_session: Session, training_template, student):
    """Добавляет студента в шаблон тренировки"""
    template_student = TrainingStudentTemplate(
        training_template_id=training_template.id,
        student_id=student.id,
        is_frozen=False,
        start_date=date.today()  # Добавляем текущую дату как start_date
    )
    db_session.add(template_student)
    db_session.commit()
    db_session.refresh(template_student)
    yield template_student
    # Удаляем привязку студента после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM training_client_templates WHERE id = :id"), {"id": template_student.id})
    db_session.commit()


def test_generate_next_week_trainings(db_session: Session, training_template, template_with_student):
    """Тест генерации тренировок на следующую неделю"""
    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    
    # Проверяем, что создана хотя бы одна тренировка
    assert created_count > 0
    assert len(trainings) > 0
    
    # Проверяем первую созданную тренировку
    training = trainings[0]
    assert training.responsible_trainer_id == training_template.responsible_trainer_id
    assert training.training_type_id == training_template.training_type_id
    assert training.start_time == training_template.start_time
    assert training.is_template_based is True
    assert training.template_id == training_template.id
    
    # Проверяем, что студент скопирован из шаблона
    students = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training.id
    ).all()
    assert len(students) == 1
    assert students[0].student_id == template_with_student.student_id
    
    # Проверяем, что дата тренировки - следующий понедельник
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    assert training.training_date == next_monday


def test_generate_next_week_endpoint_as_admin(client, auth_headers, training_template, template_with_student):
    """Тест эндпойнта генерации тренировок от имени админа"""
    response = client.post("/real-trainings/generate-next-week", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["created_count"] > 0
    assert len(data["trainings"]) > 0


def test_generate_next_week_duplicate_prevention(db_session: Session, training_template):
    """Тест предотвращения дублирования тренировок при повторной генерации"""
    # Первая генерация
    first_count, _ = generate_next_week_trainings(db_session)
    assert first_count > 0
    
    # Вторая генерация
    second_count, _ = generate_next_week_trainings(db_session)
    assert second_count == 0  # Не должно быть создано новых тренировок


def test_generate_next_week_with_multiple_templates(db_session: Session, training_type, trainer):
    """Тест генерации тренировок с несколькими шаблонами"""
    # Создаем два шаблона на разные дни недели
    template1 = TrainingTemplate(
        day_number=1,  # Понедельник
        start_time=time(10, 0),
        responsible_trainer_id=trainer.id,
        training_type_id=training_type.id
    )
    template2 = TrainingTemplate(
        day_number=3,  # Среда
        start_time=time(15, 0),
        responsible_trainer_id=trainer.id,
        training_type_id=training_type.id
    )
    db_session.add_all([template1, template2])
    db_session.commit()
    
    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    
    # Проверяем, что созданы тренировки для обоих шаблонов
    assert created_count == 2
    assert len(trainings) == 2
    
    # Проверяем, что тренировки созданы на разные дни
    training_days = {training.training_date.weekday() for training in trainings}
    assert len(training_days) == 2
    assert 0 in training_days  # Понедельник
    assert 2 in training_days  # Среда


def test_generate_next_week_with_inactive_template(db_session: Session, training_template):
    """Тест генерации тренировок с неактивным тренером"""
    # Деактивируем тренера
    training_template.responsible_trainer.is_active = False
    db_session.commit()
    
    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    
    # Проверяем, что тренировки не созданы
    assert created_count == 0
    assert len(trainings) == 0


def test_generate_next_week_with_frozen_student(db_session: Session, training_template, template_with_student):
    """Тест генерации тренировок с замороженным студентом"""
    # Замораживаем студента
    template_with_student.is_frozen = True
    db_session.commit()
    
    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    
    # Проверяем, что тренировки созданы
    assert created_count > 0
    assert len(trainings) > 0
    
    # Проверяем, что замороженный студент не добавлен
    training = trainings[0]
    students = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training.id
    ).all()
    assert len(students) == 0


def test_cancel_training_as_admin(client, auth_headers, training_template, template_with_student):
    """Тест отмены тренировки администратором"""
    # Создаем тренировку через генерацию
    response = client.post("/real-trainings/generate-next-week", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    training_id = response.json()["trainings"][0]["id"]
    
    # Отменяем тренировку
    cancellation_data = {
        "reason": "Test cancellation",
        "process_refunds": True
    }
    response = client.post(
        f"/real-trainings/{training_id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Проверяем что тренировка отменена
    cancelled_training = response.json()
    assert cancelled_training["cancelled_at"] is not None
    assert cancelled_training["cancellation_reason"] == "Test cancellation"
    
    # Проверяем что все студенты отмечены как отмененные
    for student in cancelled_training["students"]:
        assert student["cancelled_at"] is not None
        assert student["cancellation_reason"] == "Test cancellation"


def test_cancel_training_as_non_admin(client, auth_headers, training_template, template_with_student, trainer, trainer_auth_headers):
    """Тест что не-администратор не может отменить тренировку"""
    # Создаем тренировку через генерацию
    response = client.post("/real-trainings/generate-next-week", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    training_id = response.json()["trainings"][0]["id"]
    
    # Пытаемся отменить тренировку от имени тренера
    cancellation_data = {
        "reason": "Test cancellation",
        "process_refunds": True
    }
    response = client.post(
        f"/real-trainings/{training_id}/cancel",
        json=cancellation_data,
        headers=trainer_auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_cancel_already_cancelled_training(client, auth_headers, training_template, template_with_student):
    """Тест что нельзя отменить уже отмененную тренировку"""
    # Создаем тренировку через генерацию
    response = client.post("/real-trainings/generate-next-week", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    training_id = response.json()["trainings"][0]["id"]
    
    # Отменяем тренировку первый раз
    cancellation_data = {
        "reason": "Test cancellation",
        "process_refunds": True
    }
    response = client.post(
        f"/real-trainings/{training_id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Пытаемся отменить второй раз
    response = client.post(
        f"/real-trainings/{training_id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST 