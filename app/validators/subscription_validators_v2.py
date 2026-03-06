"""Валидаторы для системы абонементов v2."""
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import StudentSubscription, Invoice, MissedSession
from app.models.invoice import InvoiceStatus
from app.crud.subscription_v2 import (
    get_active_or_pending_subscription,
    count_subscription_only_visits,
    get_oldest_valid_excused_missed_session,
    get_system_setting,
)
from app.services.subscription_v2 import _get_monday


def validate_subscription_for_training_v2(
    db: Session,
    student_id: int,
    training_date: date,
    training_is_subscription_only: bool,
) -> Tuple[bool, str, Optional[StudentSubscription], Optional[MissedSession]]:
    """Валидация записи студента на тренировку (v2).

    Возвращает (is_valid, error_message, subscription, makeup_missed_session).

    Порядок проверок:
    1. Есть активный/pending абонемент, покрывающий training_date?
    2. Студент — должник + debt_behavior = BLOCK_ACCESS?
    3. Тренировка не subscription_only → разрешено (early exit).
    4. Недельный лимит. Если достигнут — ищем excused пропуск для отработки.
    """
    # 1. Проверяем наличие абонемента
    subscription = get_active_or_pending_subscription(db, student_id, training_date)
    if not subscription:
        return False, "Нет активного абонемента на дату тренировки", None, None

    # 2. Должник
    is_debtor = (
        db.query(Invoice)
        .filter(
            Invoice.student_id == student_id,
            Invoice.status == InvoiceStatus.UNPAID,
        )
        .first()
    ) is not None

    if is_debtor:
        debt_behavior = get_system_setting(db, "debt_behavior", "HIGHLIGHT_ONLY")
        if debt_behavior == "BLOCK_ACCESS":
            return False, "Доступ заблокирован: задолженность по оплате", None, None
        # HIGHLIGHT_ONLY — запись продолжается

    # 3. Если тренировка не subscription_only — разрешено без проверки лимита
    if not training_is_subscription_only:
        return True, "", subscription, None

    # 4. Недельный лимит (Пн-Вс)
    week_start = _get_monday(training_date)
    week_end = week_start + timedelta(days=6)

    sessions_per_week = subscription.subscription.sessions_per_week or 0
    weekly_count = count_subscription_only_visits(db, student_id, week_start, week_end)

    if weekly_count < sessions_per_week:
        # Лимит не достигнут — обычная запись
        return True, "", subscription, None

    # Лимит достигнут — пробуем отработку
    makeup_session = get_oldest_valid_excused_missed_session(db, student_id)
    if makeup_session:
        return True, "", subscription, makeup_session

    return (
        False,
        f"Превышен недельный лимит ({sessions_per_week} тренировок в неделю)",
        None,
        None,
    )
