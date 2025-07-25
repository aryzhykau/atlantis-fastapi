from datetime import date, time, datetime, timedelta, timezone
import json
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
    StudentSubscription,
    Subscription,
    Invoice,
    InvoiceType,
    InvoiceStatus
)
from app.models.user import UserRole
from app.schemas.attendance import AttendanceStatus
from app.crud.real_training import generate_next_week_trainings


@pytest.fixture
def training_type(db_session: Session):
    """Создает тестовый тип тренировки"""
    training_type = TrainingType(
        name="Test Training",
        color="#FF0000",
        price=100.0,
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


@pytest.fixture
def student_subscription(db_session: Session, student, training_type):
    """Создает активный абонемент для студента"""
    # Создаем подписку
    subscription = Subscription(
        name="Test Subscription",
        price=100.0,
        number_of_sessions=10,
        validity_days=60,
        is_active=True
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    
    # Создаем студентскую подписку
    student_subscription = StudentSubscription(
        student_id=student.id,
        subscription_id=subscription.id,
        start_date=date.today() - timedelta(days=30),  # Начался месяц назад
        end_date=date.today() + timedelta(days=30),    # Заканчивается через месяц
        sessions_left=10,  # 10 занятий осталось
        is_auto_renew=False
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    yield student_subscription
    # Удаляем абонемент после всех зависимых объектов
    db_session.execute(text("DELETE FROM real_training_students"))
    db_session.execute(text("DELETE FROM student_subscriptions WHERE id = :id"), {"id": student_subscription.id})
    db_session.execute(text("DELETE FROM subscriptions WHERE id = :id"), {"id": subscription.id})
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
    """Тест эндпойнта генерации тренировок с API ключом"""
    # Эндпоинт использует API ключ для cron-задач, а не JWT токены
    api_headers = {"X-API-Key": "test-cron-api-key-12345"}
    response = client.post("/real-trainings/generate-next-week", headers=api_headers)
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
    api_headers = {"X-API-Key": "test-cron-api-key-12345"}
    response = client.post("/real-trainings/generate-next-week", headers=api_headers)
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
    api_headers = {"X-API-Key": "test-cron-api-key-12345"}
    response = client.post("/real-trainings/generate-next-week", headers=api_headers)
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
    api_headers = {"X-API-Key": "test-cron-api-key-12345"}
    response = client.post("/real-trainings/generate-next-week", headers=api_headers)
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


# Тесты для отмены студентов
def test_cancel_student_safe_cancellation(client, auth_headers, training_template, template_with_student, student_subscription, db_session):
    """Тест безопасной отмены студента (>12 часов до начала) - инвойс должен отменяться"""
    # Создаем тренировку на завтра (безопасная отмена)
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        status=AttendanceStatus.REGISTERED
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Симулируем что процессинг уже произошел - устанавливаем флаг processed_at
    training.processed_at = datetime.now(timezone.utc)
    # И списываем занятие с абонемента
    student_subscription.sessions_left -= 1
    db_session.commit()
    db_session.refresh(student_subscription)
    
    sessions_before = student_subscription.sessions_left  # Теперь 7 занятий
    
    # Создаем инвойс для студента (симулируем что инвойс уже создан)
    student = db_session.query(Student).filter(Student.id == template_with_student.student_id).first()
    invoice = Invoice(
        client_id=student.client_id,
        student_id=student.id,
        training_id=training.id,
        type=InvoiceType.TRAINING,
        amount=500.0,
        status=InvoiceStatus.UNPAID,
        description="Тестовый инвойс"
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Запоминаем начальный баланс клиента
    initial_balance = student.client.balance
    
    # Отменяем участие студента (безопасная отмена)
    cancellation_data = {
        "reason": "Тестовая безопасная отмена",
        "notification_time": (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
    }

    response = client.request(
        "DELETE",
        f"/real-trainings/{training.id}/students/{template_with_student.student_id}/cancel",
        headers={**auth_headers, "Content-Type": "application/json"},
        json=cancellation_data
    )

    assert response.status_code == 204
    
    # Проверяем что статус студента изменен на безопасную отмену
    db_session.refresh(student_training)
    assert student_training.status == AttendanceStatus.CANCELLED_SAFE
    assert student_training.cancellation_reason == "Тестовая безопасная отмена"
    
    # Проверяем что инвойс отменен
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.CANCELLED
    assert invoice.cancelled_at is not None
    
    # Проверяем что средства возвращены на баланс клиента
    db_session.refresh(student.client)
    assert student.client.balance == initial_balance + 500.0
    
    # Проверяем что занятие возвращено в абонемент (так как процессинг уже произошел)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == sessions_before + 1  # Стало 8 занятий


def test_cancel_training_with_refunds(client, auth_headers, training_template, template_with_student, student_subscription, db_session):
    """Тест полной отмены тренировки с обработкой финансовых возвратов"""
    # Создаем тренировку на завтра
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        status=AttendanceStatus.REGISTERED
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Симулируем что процессинг уже произошел - устанавливаем флаг processed_at
    training.processed_at = datetime.now(timezone.utc)
    # И списываем занятие с абонемента
    student_subscription.sessions_left -= 1
    db_session.commit()
    db_session.refresh(student_subscription)
    
    sessions_before = student_subscription.sessions_left  # Теперь 7 занятий
    
    # Создаем инвойс для студента (симулируем что инвойс уже создан)
    student = db_session.query(Student).filter(Student.id == template_with_student.student_id).first()
    invoice = Invoice(
        client_id=student.client_id,
        student_id=student.id,
        training_id=training.id,
        type=InvoiceType.TRAINING,
        amount=500.0,
        status=InvoiceStatus.UNPAID,
        description="Тестовый инвойс"
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Запоминаем начальный баланс клиента
    initial_balance = student.client.balance
    
    # Отменяем тренировку
    cancellation_data = {
        "reason": "Тестовая отмена",
        "process_refunds": True
    }
    
    response = client.post(
        f"/real-trainings/{training.id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Проверяем что тренировка отменена
    db_session.refresh(training)
    assert training.cancelled_at is not None
    assert training.cancellation_reason == "Тестовая отмена"
    
    # Проверяем что инвойс отменен
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.CANCELLED
    assert invoice.cancelled_at is not None
    
    # Проверяем что средства возвращены на баланс клиента
    db_session.refresh(student.client)
    assert student.client.balance == initial_balance + 500.0
    
    # Проверяем что занятие возвращено в абонемент (так как процессинг уже произошел)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == sessions_before + 1  # Стало 8 занятий


def test_cancel_student_unsafe_cancellation(client, auth_headers, training_template, template_with_student, student_subscription, db_session):
    """Тест небезопасной отмены студента (<12 часов до начала) - занятие должно списываться как штраф"""
    # Создаем тренировку на сегодня (небезопасная отмена)
    today = date.today()
    training = RealTraining(
        training_date=today,
        start_time=time(20, 0),  # 20:00 сегодня
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку с привязкой к абонементу
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        subscription_id=student_subscription.id
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Запоминаем количество занятий до отмены
    sessions_before = student_subscription.sessions_left
    
    # Отменяем студента (небезопасная отмена)
    notification_time = datetime.now() - timedelta(hours=2)  # 2 часа до начала
    response = client.request(
        "DELETE",
        f"/real-trainings/{training.id}/students/{template_with_student.student_id}/cancel",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "notification_time": notification_time.isoformat(),
            "reason": "Unsafe cancellation test"
        }
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем, что студент остается в тренировке с статусом отмены
    remaining_students = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training.id
    ).all()
    assert len(remaining_students) == 1
    assert remaining_students[0].status == AttendanceStatus.CANCELLED_PENALTY
    assert remaining_students[0].cancelled_at is not None
    
    # Проверяем, что занятие списалось с абонемента как штраф (небезопасная отмена)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == sessions_before - 1


def test_cancel_student_unsafe_cancellation_no_subscription(client, auth_headers, training_template, template_with_student, db_session):
    """Тест небезопасной отмены студента без абонемента - должен создаться штрафной инвойс"""
    # Создаем тренировку на сегодня (небезопасная отмена)
    today = date.today()
    training = RealTraining(
        training_date=today,
        start_time=time(20, 0),  # 20:00 сегодня
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку БЕЗ абонемента
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        subscription_id=None  # Нет абонемента
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Отменяем студента (небезопасная отмена)
    notification_time = datetime.now() - timedelta(hours=2)  # 2 часа до начала
    response = client.request(
        "DELETE",
        f"/real-trainings/{training.id}/students/{template_with_student.student_id}/cancel",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "notification_time": notification_time.isoformat(),
            "reason": "Unsafe cancellation without subscription"
        }
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем, что студент остается в тренировке с статусом отмены
    remaining_students = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training.id
    ).all()
    assert len(remaining_students) == 1
    assert remaining_students[0].status == AttendanceStatus.CANCELLED_PENALTY
    assert remaining_students[0].cancelled_at is not None
    
    # Проверяем, что создался штрафной инвойс
    penalty_invoices = db_session.query(Invoice).filter(
        Invoice.student_id == template_with_student.student_id,
        Invoice.type == InvoiceType.LATE_CANCELLATION_FEE
    ).all()
    assert len(penalty_invoices) == 1
    assert penalty_invoices[0].amount == training.training_type.price


def test_cancel_student_multiple_cancellations(client, auth_headers, training_template, template_with_student, db_session):
    """Тест множественных отмен студента (отмены не ограничены)"""
    # Создаем 5 тренировок в текущем месяце и отменяем студента с каждой
    today = date.today()
    trainings = []
    
    for i in range(5):
        training = RealTraining(
            training_date=today,  # Все тренировки на сегодня - небезопасная отмена
            start_time=time(20, 0),
            responsible_trainer_id=training_template.responsible_trainer_id,
            training_type_id=training_template.training_type_id,
            template_id=training_template.id,
            is_template_based=True
        )
        db_session.add(training)
        db_session.commit()
        db_session.refresh(training)
        trainings.append(training)
        
        # Добавляем студента
        student_training = RealTrainingStudent(
            real_training_id=training.id,
            student_id=template_with_student.student_id
        )
        db_session.add(student_training)
        db_session.commit()
    
    # Отменяем студента со всех 5 тренировок (должно пройти, так как отмены не ограничены)
    for i in range(5):
        notification_time = datetime.now() - timedelta(hours=2)
        response = client.request(
            "DELETE",
            f"/real-trainings/{trainings[i].id}/students/{template_with_student.student_id}/cancel",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "notification_time": notification_time.isoformat(),
                "reason": f"Cancellation {i+1}"
            }
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем, что все студенты отмечены как отмененные
    for training in trainings:
        remaining_students = db_session.query(RealTrainingStudent).filter(
            RealTrainingStudent.real_training_id == training.id
        ).all()
        assert len(remaining_students) == 1
        assert remaining_students[0].status == AttendanceStatus.CANCELLED_PENALTY
        assert remaining_students[0].cancelled_at is not None


def test_cancel_student_not_found(client, auth_headers, training_template, db_session):
    """Тест отмены несуществующего студента"""
    # Создаем тренировку
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Пытаемся отменить несуществующего студента
    notification_time = datetime.now() - timedelta(hours=13)
    response = client.request(
        "DELETE",
        f"/real-trainings/{training.id}/students/999/cancel",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "notification_time": notification_time.isoformat(),
            "reason": "Non-existent student"
        }
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "студент не найден" in response.json()["detail"].lower()


def test_cancel_student_training_not_found(client, auth_headers, template_with_student):
    """Тест отмены студента с несуществующей тренировки"""
    notification_time = datetime.now() - timedelta(hours=13)
    response = client.request(
        "DELETE",
        f"/real-trainings/999/students/{template_with_student.student_id}/cancel",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "notification_time": notification_time.isoformat(),
            "reason": "Non-existent training"
        }
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "не найдена" in response.json()["detail"].lower()


def test_cancel_student_unauthorized(client, training_template, template_with_student, db_session):
    """Тест отмены студента без авторизации"""
    # Создаем тренировку
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Пытаемся отменить без авторизации
    notification_time = datetime.now() - timedelta(hours=13)
    response = client.request(
        "DELETE",
        f"/real-trainings/{training.id}/students/{template_with_student.student_id}/cancel",
        headers={"Content-Type": "application/json"},
        json={
            "notification_time": notification_time.isoformat(),
            "reason": "Unauthorized cancellation"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_cancel_training_before_processing(client, auth_headers, training_template, template_with_student, student_subscription, db_session):
    """Тест отмены тренировки ДО процессинга (занятие НЕ возвращается)"""
    # Создаем тренировку на завтра
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        status=AttendanceStatus.REGISTERED
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Запоминаем количество занятий в абонементе
    sessions_before = student_subscription.sessions_left
    
    # Отменяем тренировку ДО процессинга (processed_at = None)
    cancellation_data = {
        "reason": "Отмена до процессинга",
        "process_refunds": True
    }
    
    response = client.post(
        f"/real-trainings/{training.id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Проверяем что тренировка отменена
    db_session.refresh(training)
    assert training.cancelled_at is not None
    
    # Проверяем что занятие НЕ возвращено в абонемент (так как процессинг еще не произошел)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == sessions_before


def test_cancel_training_after_processing(client, auth_headers, training_template, template_with_student, student_subscription, db_session):
    """Тест отмены тренировки ПОСЛЕ процессинга (занятие возвращается)"""
    # Создаем тренировку на завтра
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
        template_id=training_template.id,
        is_template_based=True
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    
    # Добавляем студента на тренировку
    student_training = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        status=AttendanceStatus.REGISTERED
    )
    db_session.add(student_training)
    db_session.commit()
    
    # Симулируем что процессинг уже произошел - устанавливаем флаг processed_at
    training.processed_at = datetime.now(timezone.utc)
    # И списываем занятие с абонемента
    student_subscription.sessions_left -= 1
    db_session.commit()
    db_session.refresh(student_subscription)
    
    sessions_before = student_subscription.sessions_left  # Теперь 7 занятий
    
    # Отменяем тренировку ПОСЛЕ процессинга (processed_at установлен)
    cancellation_data = {
        "reason": "Отмена после процессинга",
        "process_refunds": True
    }
    
    response = client.post(
        f"/real-trainings/{training.id}/cancel",
        json=cancellation_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Проверяем что тренировка отменена
    db_session.refresh(training)
    assert training.cancelled_at is not None
    
    # Проверяем что занятие возвращено в абонемент (так как процессинг уже произошел)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == sessions_before + 1  # Стало 8 занятий


def test_generate_next_week_endpoint_wrong_api_key(client):
    """Тест эндпойнта генерации с неверным API ключом"""
    api_headers = {"X-API-Key": "wrong-key"}
    response = client.post("/real-trainings/generate-next-week", headers=api_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_generate_next_week_endpoint_no_api_key(client):
    """Тест эндпойнта генерации без API ключа"""
    response = client.post("/real-trainings/generate-next-week")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_generate_next_week_with_inactive_trainer(db_session: Session, training_template, trainer):
    """Тест, что тренировки не создаются для шаблона с неактивным тренером."""
    # Делаем тренера неактивным
    trainer.is_active = False
    db_session.commit()

    # Пытаемся сгенерировать тренировки
    created_count, _ = generate_next_week_trainings(db_session)

    # Проверяем, что тренировки не были созданы
    assert created_count == 0


def test_generate_next_week_with_inactive_training_type(db_session: Session, training_template, training_type):
    """Тест, что тренировки не создаются для шаблона с неактивным типом тренировки."""
    # Делаем тип тренировки неактивным
    training_type.is_active = False
    db_session.commit()

    # Пытаемся сгенерировать тренировки
    created_count, _ = generate_next_week_trainings(db_session)

    # Проверяем, что тренировки не были созданы
    assert created_count == 0


def test_generate_next_week_with_future_start_date_student(db_session: Session, training_template, template_with_student):
    """Тест, что студент с будущей датой начала не добавляется в тренировку."""
    # Устанавливаем дату начала в будущем
    template_with_student.start_date = date.today() + timedelta(days=30)
    db_session.commit()

    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)

    assert created_count > 0  # Тренировка должна быть создана

    # Проверяем, что студент не был добавлен
    students_count = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == trainings[0].id
    ).count()
    assert students_count == 0


def test_generate_next_week_max_participants_limit(db_session: Session, training_type, training_template, student, create_test_client):
    """Тест, что соблюдается лимит max_participants."""
    # Устанавливаем лимит участников
    training_type.max_participants = 1
    db_session.commit()

    # Создаем второго студента
    student2 = Student(
        first_name="Second",
        last_name="Student",
        date_of_birth=date(2001, 1, 1),
        is_active=True,
        client_id=create_test_client.id
    )
    db_session.add(student2)
    db_session.commit()

    # Добавляем обоих студентов в шаблон
    db_session.add_all([
        TrainingStudentTemplate(
            training_template_id=training_template.id,
            student_id=student.id,
            is_frozen=False,
            start_date=date.today()
        ),
        TrainingStudentTemplate(
            training_template_id=training_template.id,
            student_id=student2.id,
            is_frozen=False,
            start_date=date.today()
        )
    ])
    db_session.commit()

    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)

    assert created_count > 0

    # Проверяем, что был добавлен только один студент
    students_count = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == trainings[0].id
    ).count()
    assert students_count == 1


def test_generate_subscription_only_training_no_subscription(db_session: Session, training_type, template_with_student):
    """Тест, что студент без абонемента не добавляется на only-subscription тренировку."""
    # Делаем тип тренировки только по абонементу
    training_type.is_subscription_only = True
    db_session.commit()

    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    assert created_count > 0

    # Проверяем, что студент не был добавлен
    students_count = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == trainings[0].id
    ).count()
    assert students_count == 0


def test_generate_subscription_only_training_with_subscription(db_session: Session, training_type, template_with_student, student_subscription):
    """Тест, что студент с абонементом добавляется на only-subscription тренировку."""
    # Делаем тип тренировки только по абонементу
    training_type.is_subscription_only = True
    db_session.commit()

    # Убедимся, что у студента есть активный абонемент (фикстура student_subscription)
    assert student_subscription.student_id == template_with_student.student_id

    # Генерируем тренировки
    created_count, trainings = generate_next_week_trainings(db_session)
    assert created_count > 0

    # Проверяем, что студент был добавлен
    students_count = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == trainings[0].id
    ).count()
    assert students_count == 1


def test_update_attendance_cannot_set_present(
    client, trainer_auth_headers, training_template, template_with_student, db_session
):
    """
    Тест: Проверяет, что API возвращает ошибку при попытке вручную
    установить статус посещения 'PRESENT'.
    """
    # Создаем реальную тренировку для теста
    training = RealTraining(
        training_date=date.today(),
        start_time=time(10, 0),
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)

    # Добавляем студента на эту тренировку
    rts = RealTrainingStudent(
        real_training_id=training.id,
        student_id=template_with_student.student_id,
        status=AttendanceStatus.REGISTERED,
    )
    db_session.add(rts)
    db_session.commit()

    # Пытаемся обновить статус на PRESENT
    update_data = {"status": AttendanceStatus.PRESENT.value}
    response = client.put(
        f"/real-trainings/{training.id}/students/{template_with_student.student_id}/attendance",
        json=update_data,
        headers=trainer_auth_headers,
    )

    # Проверяем, что сервер вернул ошибку валидации
    assert response.status_code == 422
    assert "Cannot manually set status to PRESENT" in response.text