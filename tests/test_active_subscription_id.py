import pytest
from datetime import datetime, timedelta, timezone, date

from app.models import Student, User, Subscription, StudentSubscription
from app.crud.student import get_student_by_id

@pytest.fixture
def test_user(db_session):
    user = User(
        email="test@example.com",
        role="ADMIN",
        first_name="Тест",
        last_name="Админ",
        date_of_birth=date(1990, 1, 1),
        phone="+79990000000"
    )
    db_session.add(user)
    db_session.commit()
    yield user
    try:
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()

@pytest.fixture
def test_subscription(db_session):
    subscription = Subscription(
        name="Тестовый абонемент",
        price=1000.0,
        number_of_sessions=8,
        validity_days=30
    )
    db_session.add(subscription)
    db_session.commit()
    yield subscription
    try:
        db_session.delete(subscription)
        db_session.commit()
    except Exception:
        db_session.rollback()

@pytest.fixture
def test_student(db_session, test_user):
    student = Student(
        client_id=test_user.id,
        first_name="Тест",
        last_name="Студент",
        date_of_birth=date(2010, 1, 1)
    )
    db_session.add(student)
    db_session.commit()
    yield student
    try:
        db_session.delete(student)
        db_session.commit()
    except Exception:
        db_session.rollback()

def test_active_subscription_id_expired(db_session, test_student, test_subscription):
    # Создаём истёкший абонемент
    start_date = datetime.now(timezone.utc) - timedelta(days=60)
    end_date = start_date + timedelta(days=30)
    expired_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=start_date,
        end_date=end_date,
        sessions_left=0,
        transferred_sessions=0
    )
    db_session.add(expired_subscription)
    db_session.commit()
    db_session.refresh(expired_subscription)

    # Устанавливаем истёкший абонемент как активный
    test_student.active_subscription_id = test_subscription.id
    db_session.commit()
    db_session.refresh(test_student)

    # Проверяем, что абонемент действительно истёк
    assert expired_subscription.status == "expired"

    # Вызываем функцию, которая должна сбросить active_subscription_id
    updated_student = get_student_by_id(db_session, test_student.id)
    db_session.refresh(updated_student)
    assert updated_student.active_subscription_id is None

def test_active_subscription_id_active(db_session, test_student, test_subscription):
    # Создаём активный абонемент
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=30)
    active_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=start_date,
        end_date=end_date,
        sessions_left=8,
        transferred_sessions=0
    )
    db_session.add(active_subscription)
    db_session.commit()
    db_session.refresh(active_subscription)

    # Устанавливаем активный абонемент как активный
    test_student.active_subscription_id = test_subscription.id
    db_session.commit()
    db_session.refresh(test_student)

    # Проверяем, что абонемент действительно активен
    assert active_subscription.status == "active"

    # Вызываем функцию, которая должна оставить active_subscription_id
    updated_student = get_student_by_id(db_session, test_student.id)
    db_session.refresh(updated_student)
    assert updated_student.active_subscription_id == test_subscription.id 