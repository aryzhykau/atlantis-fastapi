from datetime import datetime, timedelta
import pytest

from app.models import Subscription, StudentSubscription


def dt_now():
    return datetime.now().replace(microsecond=0)

@pytest.fixture
def test_subscription(db_session):
    """
    Создает тестовый абонемент в базе данных.
    """
    subscription = Subscription(
        name="Test Subscription",
        price=100.0,
        number_of_sessions=8,
        validity_days=30,
        is_active=True
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def test_student_subscription(db_session, test_student, test_subscription):
    """
    Создает тестовую подписку студента в базе данных.
    """
    now = dt_now()
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now,
        end_date=now + timedelta(days=30),
        sessions_left=test_subscription.number_of_sessions,
        transferred_sessions=0,
        is_auto_renew=False,
        freeze_start_date=None,
        freeze_end_date=None
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_auto_renewal_subscription(db_session, test_student, test_subscription):
    """
    Создает тестовую подписку студента с автопродлением в базе данных.
    """
    now = dt_now()
    today_end = now.replace(hour=23, minute=59, second=59)
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now - timedelta(days=25),  # Началась 25 дней назад
        end_date=today_end,  # Заканчивается в конце дня сегодня
        sessions_left=test_subscription.number_of_sessions,
        transferred_sessions=0,
        is_auto_renew=True,
        freeze_start_date=None,
        freeze_end_date=None
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_student_subscription_expired(db_session, test_student, test_subscription):
    """
    Создает истекший абонемент студента
    """
    now = dt_now()
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now - timedelta(days=35),
        end_date=now - timedelta(days=5),
        sessions_left=0,
        transferred_sessions=0,
        is_auto_renew=False,
        freeze_start_date=None,
        freeze_end_date=None
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_frozen_subscription(db_session, test_student, test_subscription):
    """
    Создает замороженную подписку студента
    """
    now = dt_now()
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now,
        end_date=now + timedelta(days=30),
        sessions_left=test_subscription.number_of_sessions,
        transferred_sessions=0,
        is_auto_renew=False,
        freeze_start_date=now,
        freeze_end_date=now + timedelta(days=7)
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_expired_frozen_subscription(db_session, test_student, test_subscription):
    """
    Создает замороженную подписку студента с истекшим сроком заморозки
    """
    now = dt_now()
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now,
        end_date=now + timedelta(days=30),
        sessions_left=test_subscription.number_of_sessions,
        transferred_sessions=0,
        is_auto_renew=False,
        freeze_start_date=now - timedelta(days=10),
        freeze_end_date=now - timedelta(days=1)  # Заморозка уже закончилась
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_subscription_with_transferred_sessions(db_session, test_student, test_subscription):
    """
    Создает подписку студента с перенесенными занятиями
    """
    now = dt_now()
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=now,
        end_date=now + timedelta(days=30),
        sessions_left=test_subscription.number_of_sessions + 3,  # +3 перенесенных занятия
        transferred_sessions=3,
        is_auto_renew=False,
        freeze_start_date=None,
        freeze_end_date=None
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_inactive_subscription(db_session):
    """
    Создает неактивный абонемент в базе данных.
    """
    subscription = Subscription(
        name="Inactive Subscription",
        price=50.0,
        number_of_sessions=4,
        validity_days=15,
        is_active=False
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription 