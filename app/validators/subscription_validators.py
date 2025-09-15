from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.models import StudentSubscription, Subscription
from app.crud import subscription as subscription_crud


# =============================================================================
# ВАЛИДАЦИЯ АБОНЕМЕНТОВ (Subscription)
# =============================================================================

def validate_subscription_exists(db: Session, subscription_id: int) -> Optional[Subscription]:
    """
    Проверка существования абонемента
    
    Returns:
        Subscription если существует, None если нет
    """
    return subscription_crud.get_subscription_by_id(db, subscription_id)


def validate_subscription_active(subscription: Subscription) -> bool:
    """
    Проверка, что абонемент активен
    
    Returns:
        True если абонемент активен, False если нет
    """
    return subscription.is_active


def validate_subscription_price_positive(subscription: Subscription) -> bool:
    """
    Проверка, что цена абонемента положительная
    
    Returns:
        True если цена положительная, False если нет
    """
    return subscription.price > 0


def validate_subscription_sessions_positive(subscription: Subscription) -> bool:
    """
    Проверка, что количество занятий в абонементе положительное
    
    Returns:
        True если количество занятий положительное, False если нет
    """
    return subscription.number_of_sessions > 0


def validate_subscription_validity_positive(subscription: Subscription) -> bool:
    """
    Проверка, что срок действия абонемента положительный
    
    Returns:
        True если срок действия положительный, False если нет
    """
    return subscription.validity_days > 0


# =============================================================================
# ВАЛИДАЦИЯ АБОНЕМЕНТОВ СТУДЕНТОВ (StudentSubscription)
# =============================================================================

def validate_student_subscription_exists(
    db: Session, 
    student_subscription_id: int
) -> Optional[StudentSubscription]:
    """
    Проверка существования абонемента студента
    
    Returns:
        StudentSubscription если существует, None если нет
    """
    return subscription_crud.get_student_subscription(db, student_subscription_id)


def validate_subscription_active_status(student_subscription: StudentSubscription) -> bool:
    """
    Проверка, что абонемент студента имеет статус 'active'
    
    Returns:
        True если статус 'active', False если нет
    """
    return student_subscription.status == 'active'


def validate_subscription_not_expired(student_subscription: StudentSubscription) -> bool:
    """
    Проверка, что абонемент студента не истёк
    
    Returns:
        True если абонемент не истёк, False если истёк
    """
    today = date.today()
    return student_subscription.end_date >= today


def validate_subscription_not_frozen(student_subscription: StudentSubscription) -> bool:
    """
    Проверка, что абонемент студента не заморожен
    
    Returns:
        True если абонемент не заморожен, False если заморожен
    """
    if student_subscription.freeze_start_date is None:
        return True
    
    today = date.today()
    return not (
        student_subscription.freeze_start_date <= today <= student_subscription.freeze_end_date
    )


def validate_sessions_available(student_subscription: StudentSubscription) -> bool:
    """
    Проверка, что в абонементе есть доступные занятия
    
    Returns:
        True если есть занятия, False если нет
    """
    return student_subscription.sessions_left > 0


def validate_subscription_date_range(
    student_subscription: StudentSubscription,
    training_date: date
) -> bool:
    """
    Проверка, что тренировка попадает в период действия абонемента
    
    Returns:
        True если тренировка в периоде действия, False если нет
    """
    return (
        student_subscription.start_date <= training_date <= student_subscription.end_date
    )


def validate_subscription_not_frozen_on_date(
    student_subscription: StudentSubscription,
    training_date: date
) -> bool:
    """
    Проверка, что абонемент не заморожен на дату тренировки
    
    Returns:
        True если не заморожен на дату, False если заморожен
    """
    if student_subscription.freeze_start_date is None:
        return True
    
    return not (
        student_subscription.freeze_start_date <= training_date <= student_subscription.freeze_end_date
    )


def validate_freeze_date_range(
    freeze_start_date: date,
    freeze_end_date: date,
    subscription_start_date: date,
    subscription_end_date: date
) -> bool:
    """
    Проверка корректности периода заморозки
    
    Returns:
        True если период заморозки корректный, False если нет
    """
    # Проверяем, что даты заморозки в правильном порядке
    if freeze_start_date >= freeze_end_date:
        return False
    
    # Проверяем, что период заморозки попадает в период действия абонемента
    if freeze_start_date < subscription_start_date or freeze_end_date > subscription_end_date:
        return False
    
    return True


def validate_subscription_can_be_frozen(
    student_subscription: StudentSubscription,
    freeze_start_date: date,
    freeze_end_date: date
) -> bool:
    """
    Проверка, можно ли заморозить абонемент
    
    Returns:
        True если можно заморозить, False если нет
    """
    # Проверяем корректность периода заморозки
    if not validate_freeze_date_range(
        freeze_start_date, 
        freeze_end_date,
        student_subscription.start_date,
        student_subscription.end_date
    ):
        return False
    
    # Проверяем, что абонемент активен
    if not validate_subscription_active_status(student_subscription):
        return False
    
    # Проверяем, что абонемент не истёк
    if not validate_subscription_not_expired(student_subscription):
        return False
    
    return True


def validate_subscription_can_be_unfrozen(
    student_subscription: StudentSubscription
) -> bool:
    """
    Проверка, можно ли разморозить абонемент
    
    Returns:
        True если можно разморозить, False если нет
    """
    # Проверяем, что абонемент заморожен
    if student_subscription.freeze_start_date is None:
        return False
    
    # Проверяем, что абонемент активен
    if not validate_subscription_active_status(student_subscription):
        return False
    
    return True


# =============================================================================
# КОМПЛЕКСНЫЕ ВАЛИДАЦИИ
# =============================================================================

def validate_subscription_for_training(
    db: Session,
    student_id: int,
    training_date: date
) -> tuple[bool, str, Optional[StudentSubscription]]:
    """
    Комплексная валидация абонемента для тренировки
    
    Returns:
        (is_valid, error_message, student_subscription)
    """
    # Получаем активный абонемент студента
    student_subscription = subscription_crud.get_active_subscription(
        db, student_id, training_date
    )
    
    if not student_subscription:
        return False, "У студента нет активного абонемента на эту дату", None
    
    # Проверяем, что абонемент активен
    if not validate_subscription_active_status(student_subscription):
        return False, "Абонемент неактивен", None
    
    # Проверяем, что абонемент не истёк
    if not validate_subscription_not_expired(student_subscription):
        return False, "Абонемент истёк", None
    
    # Проверяем, что есть доступные занятия
    if not validate_sessions_available(student_subscription):
        return False, "В абонементе нет доступных занятий", None
    
    # Проверяем, что абонемент не заморожен на дату тренировки
    if not validate_subscription_not_frozen_on_date(student_subscription, training_date):
        return False, "Абонемент заморожен на эту дату", None
    
    return True, "", student_subscription


def validate_subscription_for_session_deduction(
    db: Session,
    student_subscription_id: int
) -> tuple[bool, str]:
    """
    Комплексная валидация для списания занятия с абонемента
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование абонемента
    student_subscription = validate_student_subscription_exists(db, student_subscription_id)
    if not student_subscription:
        return False, "Абонемент студента не найден"
    
    # Проверяем, что абонемент активен
    if not validate_subscription_active_status(student_subscription):
        return False, "Абонемент неактивен"
    
    # Проверяем, что абонемент не истёк
    if not validate_subscription_not_expired(student_subscription):
        return False, "Абонемент истёк"
    
    # Проверяем, что есть доступные занятия
    if not validate_sessions_available(student_subscription):
        return False, "В абонементе нет доступных занятий"
    
    return True, ""


def validate_subscription_for_freeze(
    db: Session,
    student_subscription_id: int,
    freeze_start_date: date,
    freeze_end_date: date
) -> tuple[bool, str]:
    """
    Комплексная валидация для заморозки абонемента
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование абонемента
    student_subscription = validate_student_subscription_exists(db, student_subscription_id)
    if not student_subscription:
        return False, "Абонемент студента не найден"
    
    # Проверяем, можно ли заморозить
    if not validate_subscription_can_be_frozen(
        student_subscription, freeze_start_date, freeze_end_date
    ):
        return False, "Абонемент нельзя заморозить"
    
    return True, ""


def validate_subscription_for_unfreeze(
    db: Session,
    student_subscription_id: int
) -> tuple[bool, str]:
    """
    Комплексная валидация для разморозки абонемента
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование абонемента
    student_subscription = validate_student_subscription_exists(db, student_subscription_id)
    if not student_subscription:
        return False, "Абонемент студента не найден"
    
    # Проверяем, можно ли разморозить
    if not validate_subscription_can_be_unfrozen(student_subscription):
        return False, "Абонемент нельзя разморозить"
    
    return True, ""


def validate_subscription_creation(
    db: Session,
    student_id: int,
    subscription_id: int,
    start_date: date,
    end_date: date,
    sessions_left: int
) -> tuple[bool, str]:
    """
    Комплексная валидация для создания абонемента студента
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование абонемента
    subscription = validate_subscription_exists(db, subscription_id)
    if not subscription:
        return False, "Абонемент не найден"
    
    # Проверяем, что абонемент активен
    if not validate_subscription_active(subscription):
        return False, "Абонемент неактивен"
    
    # Проверяем корректность дат
    if start_date >= end_date:
        return False, "Дата начала должна быть раньше даты окончания"
    
    # Проверяем корректность количества занятий
    if sessions_left <= 0:
        return False, "Количество занятий должно быть положительным"
    
    if sessions_left > subscription.number_of_sessions:
        return False, "Количество занятий превышает лимит абонемента"
    
    return True, "" 