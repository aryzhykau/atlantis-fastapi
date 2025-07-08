import pytest
from datetime import datetime, timedelta, timezone

from app.models import StudentSubscription
from app.services.subscription import SubscriptionService

def test_freeze_and_unfreeze_logic(db_session, test_student, test_subscription, test_admin):
    """Тест логики заморозки и разморозки абонементов"""
    
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
    
    # Проверяем исходное состояние
    assert student_subscription.status == "active"
    assert student_subscription.freeze_start_date is None
    assert student_subscription.freeze_end_date is None
    
    # Тестируем заморозку (начинаем сейчас, а не в будущем)
    service = SubscriptionService(db_session)
    freeze_start = datetime.now(timezone.utc)  # Заморозка начинается сейчас
    freeze_duration = 7
    
    frozen_subscription = service.freeze_subscription(
        student_subscription_id=student_subscription.id,
        freeze_start_date=freeze_start,
        freeze_duration_days=freeze_duration,
        updated_by_id=test_admin.id
    )
    
    # Проверяем, что абонемент заморожен
    assert frozen_subscription.status == "frozen"
    # Сравниваем даты без timezone, так как в БД они сохраняются без timezone
    assert frozen_subscription.freeze_start_date.replace(tzinfo=None) == freeze_start.replace(tzinfo=None)
    assert frozen_subscription.freeze_end_date.replace(tzinfo=None) == (freeze_start + timedelta(days=freeze_duration)).replace(tzinfo=None)
    
    # Тестируем разморозку
    unfrozen_subscription = service.unfreeze_subscription(
        student_subscription_id=student_subscription.id,
        updated_by_id=test_admin.id
    )
    
    # Проверяем, что абонемент разморожен
    assert unfrozen_subscription.status == "active"
    assert unfrozen_subscription.freeze_start_date is None
    assert unfrozen_subscription.freeze_end_date is None 