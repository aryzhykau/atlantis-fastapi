import pytest
from datetime import datetime, timedelta, timezone

from app.models import StudentSubscription
from app.services.subscription import SubscriptionService

def test_auto_unfreeze_expired_subscriptions(db_session, test_student, test_subscription, test_admin):
    """Тест авторазморозки абонементов с истёкшей заморозкой"""
    
    # Создаем абонемент студента
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=30)
    
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=start_date,
        end_date=end_date,
        sessions_left=8,
        transferred_sessions=0
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    
    # Замораживаем абонемент с истёкшей заморозкой
    service = SubscriptionService(db_session)
    freeze_start = datetime.now(timezone.utc) - timedelta(days=10)  # Заморозка началась 10 дней назад
    freeze_duration = 5  # Заморозка на 5 дней
    
    frozen_subscription = service.freeze_subscription(
        student_subscription_id=student_subscription.id,
        freeze_start_date=freeze_start,
        freeze_duration_days=freeze_duration,
        updated_by_id=test_admin.id
    )
    
    # Проверяем, что заморозка истёкла (freeze_end_date в прошлом)
    current_time = datetime.now(timezone.utc)
    freeze_end = freeze_start + timedelta(days=freeze_duration)
    assert freeze_end < current_time, "Заморозка должна быть истёкшей"
    
    # Запускаем авторазморозку
    unfrozen_subscriptions = service.auto_unfreeze_expired_subscriptions(admin_id=test_admin.id)
    
    # Проверяем, что абонемент был разморожен
    assert len(unfrozen_subscriptions) == 1
    
    # Обновляем данные из БД
    db_session.refresh(student_subscription)
    
    # Проверяем, что поля заморозки сброшены
    assert student_subscription.freeze_start_date is None
    assert student_subscription.freeze_end_date is None


def test_auto_unfreeze_skips_active_freeze(db_session, test_student, test_subscription, test_admin):
    """Тест, что авторазморозка не трогает абонементы с активной заморозкой."""
    
    # Создаем абонемент
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
        sessions_left=8
    )
    db_session.add(student_subscription)
    db_session.commit()
    
    # Замораживаем так, чтобы заморозка была активна
    service = SubscriptionService(db_session)
    freeze_start = datetime.now(timezone.utc) - timedelta(days=2)
    freeze_duration = 5 # Заканчивается через 3 дня
    
    service.freeze_subscription(
        student_subscription_id=student_subscription.id,
        freeze_start_date=freeze_start,
        freeze_duration_days=freeze_duration,
        updated_by_id=test_admin.id
    )

    # Запускаем авторазморозку
    unfrozen_subscriptions = service.auto_unfreeze_expired_subscriptions(admin_id=test_admin.id)
    
    # Проверяем, что ничего не было разморожено
    assert len(unfrozen_subscriptions) == 0
    
    # Проверяем, что поля заморозки остались на месте
    db_session.refresh(student_subscription)
    assert student_subscription.freeze_start_date is not None
    assert student_subscription.freeze_end_date is not None 