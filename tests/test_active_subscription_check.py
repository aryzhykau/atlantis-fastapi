#!/usr/bin/env python3
"""
Тест для проверки логики обновления active_subscription_id
при истечении абонемента студента.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import StudentSubscription
from app.crud.student import get_student_by_id

def test_active_subscription_id_expired(db_session, test_student, test_subscription):
    """Тест сброса active_subscription_id для истёкшего абонемента"""
    
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
    """Тест сохранения active_subscription_id для активного абонемента"""
    
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


if __name__ == "__main__":
    pytest.main() 