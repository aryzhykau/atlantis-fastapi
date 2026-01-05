from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Subscription, StudentSubscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.schemas.subscription import StudentSubscriptionCreate, StudentSubscriptionUpdate


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ С АБОНЕМЕНТАМИ (Subscription)
# =============================================================================

def get_subscriptions(db: Session) -> List[Subscription]:
    """
    Получение списка всех абонементов
    """
    return db.query(Subscription).all()


def get_subscription_by_id(db: Session, subscription_id: int) -> Optional[Subscription]:
    """
    Получение конкретного абонемента по ID
    """
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()


def get_subscription_by_name(db: Session, name: str) -> Optional[Subscription]:
    """
    Получение абонемента по названию
    """
    return db.query(Subscription).filter(Subscription.name == name).first()


def get_active_subscriptions(db: Session) -> List[Subscription]:
    """
    Получение только активных абонементов
    """
    return db.query(Subscription).filter(Subscription.is_active == True).all()


def create_subscription(db: Session, subscription: SubscriptionCreate) -> Subscription:
    """
    Создание нового абонемента
    """
    db_subscription = Subscription(
        name=subscription.name,
        price=subscription.price,
        number_of_sessions=subscription.number_of_sessions,
        validity_days=subscription.validity_days,
        is_active=subscription.is_active,
    )
    db.add(db_subscription)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(db_subscription)
    return db_subscription


def update_subscription(
    db: Session, 
    subscription_id: int, 
    updated_data: SubscriptionUpdate
) -> Optional[Subscription]:
    """
    Обновление существующего абонемента
    """
    db_subscription = get_subscription_by_id(db, subscription_id)
    if not db_subscription:
        return None
        
    for key, value in updated_data.model_dump(exclude_unset=True).items():
        setattr(db_subscription, key, value)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(db_subscription)
    return db_subscription


def delete_subscription(db: Session, subscription_id: int) -> bool:
    """
    Удаление абонемента
    """
    db_subscription = get_subscription_by_id(db, subscription_id)
    if not db_subscription:
        return False

    db.delete(db_subscription)
    # НЕ делаем commit здесь - это делает сервис
    return True


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ С АБОНЕМЕНТАМИ СТУДЕНТОВ (StudentSubscription)
# =============================================================================

def get_student_subscription(
    db: Session, 
    student_subscription_id: int
) -> Optional[StudentSubscription]:
    """
    Получение абонемента студента по ID
    """
    return db.query(StudentSubscription).filter(
        StudentSubscription.id == student_subscription_id
    ).first()


def get_student_subscriptions(
    db: Session,
    student_id: int,
    *,
    status: Optional[str] = None,
    include_expired: bool = False,
) -> List[StudentSubscription]:
    """
    Получение абонементов студента
    """
    from datetime import datetime
    query = db.query(StudentSubscription).filter(
        StudentSubscription.student_id == student_id
    )
    now = datetime.now().replace(microsecond=0)
    if status:
        if status == "active":
            query = query.filter(
                StudentSubscription.start_date <= now,
                StudentSubscription.end_date >= now,
                (
                    (StudentSubscription.freeze_start_date.is_(None)) |
                    (
                        (StudentSubscription.freeze_start_date.isnot(None)) &
                        (StudentSubscription.freeze_end_date.isnot(None)) &
                        ((StudentSubscription.freeze_start_date > now) |
                         (StudentSubscription.freeze_end_date < now))
                    )
                )
            )
        elif status == "pending":
            query = query.filter(StudentSubscription.start_date > now)
        elif status == "frozen":
            query = query.filter(
                StudentSubscription.freeze_start_date.isnot(None),
                StudentSubscription.freeze_end_date.isnot(None),
                StudentSubscription.freeze_start_date <= now,
                StudentSubscription.freeze_end_date >= now
            )
        elif status == "expired":
            query = query.filter(StudentSubscription.end_date < now)
    if not include_expired:
        query = query.filter(StudentSubscription.end_date >= now)
    return query.order_by(StudentSubscription.start_date.desc()).all()


def get_student_subscriptions_by_status(
    db: Session,
    student_id: int,
    status: str,
) -> List[StudentSubscription]:
    """
    Получение абонементов студента по статусу
    """
    from datetime import datetime
    now = datetime.now().replace(microsecond=0)
    if status == "active":
        return db.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.start_date <= now,
            StudentSubscription.end_date >= now,
            (
                (StudentSubscription.freeze_start_date.is_(None)) |
                (
                    (StudentSubscription.freeze_start_date.isnot(None)) &
                    (StudentSubscription.freeze_end_date.isnot(None)) &
                    ((StudentSubscription.freeze_start_date > now) |
                     (StudentSubscription.freeze_end_date < now))
                )
            )
        ).order_by(StudentSubscription.start_date.desc()).all()
    elif status == "pending":
        return db.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.start_date > now
        ).order_by(StudentSubscription.start_date.desc()).all()
    elif status == "frozen":
        return db.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.freeze_start_date.isnot(None),
            StudentSubscription.freeze_end_date.isnot(None),
            StudentSubscription.freeze_start_date <= now,
            StudentSubscription.freeze_end_date >= now
        ).order_by(StudentSubscription.start_date.desc()).all()
    elif status == "expired":
        return db.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.end_date < now
        ).order_by(StudentSubscription.start_date.desc()).all()
    else:
        return []


def get_active_subscription(
    db: Session,
    student_id: int,
    training_date: date,
) -> Optional[StudentSubscription]:
    """
    Получение активного абонемента студента на дату тренировки
    """
    from datetime import datetime
    training_datetime = datetime.combine(training_date, datetime.min.time()).replace(microsecond=0)
    return db.query(StudentSubscription).filter(
        StudentSubscription.student_id == student_id,
        StudentSubscription.start_date <= training_datetime,
        StudentSubscription.end_date >= training_datetime,
        StudentSubscription.sessions_left > 0,
        (
            (StudentSubscription.freeze_start_date.is_(None)) |
            (
                (StudentSubscription.freeze_start_date.isnot(None)) &
                (StudentSubscription.freeze_end_date.isnot(None)) &
                ((StudentSubscription.freeze_start_date > training_datetime) |
                 (StudentSubscription.freeze_end_date < training_datetime))
            )
        )
    ).first()


def get_active_student_subscriptions(
    db: Session,
    student_id: int,
) -> List[StudentSubscription]:
    """
    Получение активных абонементов студента
    """
    from datetime import datetime
    now = datetime.now().replace(microsecond=0)
    return db.query(StudentSubscription).filter(
        StudentSubscription.student_id == student_id,
        StudentSubscription.start_date <= now,
        StudentSubscription.end_date >= now,
        (
            (StudentSubscription.freeze_start_date.is_(None)) |
            (
                (StudentSubscription.freeze_start_date.isnot(None)) &
                (StudentSubscription.freeze_end_date.isnot(None)) &
                ((StudentSubscription.freeze_start_date > now) |
                 (StudentSubscription.freeze_end_date < now))
            )
        )
    ).all()


def create_student_subscription(
    db: Session,
    subscription_data: StudentSubscriptionCreate,
) -> StudentSubscription:
    """
    Создание абонемента для студента
    """
    student_subscription = StudentSubscription(
        student_id=subscription_data.student_id,
        subscription_id=subscription_data.subscription_id,
        start_date=subscription_data.start_date,
        end_date=subscription_data.end_date,
        sessions_left=subscription_data.sessions_left,
        transferred_sessions=subscription_data.transferred_sessions,
        is_auto_renew=subscription_data.is_auto_renew,
        freeze_start_date=subscription_data.freeze_start_date,
        freeze_end_date=subscription_data.freeze_end_date,
    )
    db.add(student_subscription)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def update_student_subscription(
    db: Session,
    student_subscription_id: int,
    update_data: StudentSubscriptionUpdate,
) -> Optional[StudentSubscription]:
    """
    Обновление абонемента студента
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(student_subscription, field, value)

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def deduct_session(
    db: Session,
    student_subscription_id: int,
) -> Optional[StudentSubscription]:
    """
    Списание занятия с абонемента
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    if student_subscription.sessions_left <= 0:
        return None  # Нет занятий для списания

    student_subscription.sessions_left -= 1
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def add_session(
    db: Session,
    student_subscription_id: int,
) -> Optional[StudentSubscription]:
    """
    Добавление занятия в абонемент
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    student_subscription.sessions_left += 1
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def check_subscription_availability(
    db: Session,
    student_id: int,
    training_date: date,
) -> Optional[StudentSubscription]:
    """
    Проверка доступности абонемента для тренировки
    """
    return get_active_subscription(db, student_id, training_date)


def get_expiring_subscriptions(
    db: Session,
    days_before_expiry: int = 7,
) -> List[StudentSubscription]:
    """
    Получение абонементов, которые скоро истекают
    """
    from datetime import datetime, timedelta
    now = datetime.now().replace(microsecond=0)
    expiry_date = now + timedelta(days=days_before_expiry)
    return db.query(StudentSubscription).filter(
        StudentSubscription.start_date <= now,
        StudentSubscription.end_date >= now,
        StudentSubscription.end_date <= expiry_date,
        (
            (StudentSubscription.freeze_start_date.is_(None)) |
            (
                (StudentSubscription.freeze_start_date.isnot(None)) &
                (StudentSubscription.freeze_end_date.isnot(None)) &
                ((StudentSubscription.freeze_start_date > now) |
                 (StudentSubscription.freeze_end_date < now))
            )
        )
    ).all()


def get_frozen_subscriptions(
    db: Session,
    current_date: Optional[datetime] = None,
) -> List[StudentSubscription]:
    """
    Получение замороженных абонементов, у которых истек срок заморозки
    """
    if current_date is None:
        current_date = datetime.now(timezone.utc)
        
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.freeze_start_date.isnot(None),
            StudentSubscription.freeze_end_date.isnot(None),
            StudentSubscription.freeze_end_date <= current_date,  # Заморозка уже закончилась
        )
    ).all()


def update_subscription_auto_renewal_invoice(
    db: Session,
    student_subscription_id: int,
    auto_renewal_invoice_id: Optional[int]
) -> Optional[StudentSubscription]:
    """
    Обновление ID инвойса автопродления для абонемента студента
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    student_subscription.auto_renewal_invoice_id = auto_renewal_invoice_id
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def get_auto_renewal_subscriptions(
    db: Session,
    days_back: int = 7
) -> List[StudentSubscription]:
    """
    Получение всех абонементов с автопродлением, которые заканчиваются сегодня или закончились в прошлые дни
    
    Args:
        days_back: Количество дней назад для поиска просроченных подписок (по умолчанию 7)
    """
    from datetime import datetime, timezone, timedelta
    
    current_time = datetime.now(timezone.utc)
    today_end = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    search_start = today_end - timedelta(days=days_back)
    
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.is_auto_renew == True,
            StudentSubscription.end_date >= search_start,
            StudentSubscription.end_date <= today_end,
            StudentSubscription.auto_renewal_invoice_id.is_(None),  # Защита от дублей
            # Исключаем замороженные подписки - если есть даты заморозки, то подписка заморожена
            or_(
                StudentSubscription.freeze_start_date.is_(None),
                and_(
                    StudentSubscription.freeze_start_date.isnot(None),
                    StudentSubscription.freeze_end_date.isnot(None),
                    # Подписка разморожена только если заморозка уже закончилась
                    StudentSubscription.freeze_end_date < current_time
                )
            )
        )
    ).with_for_update(skip_locked=True).all()


def get_today_auto_renewal_subscriptions(
    db: Session,
) -> List[StudentSubscription]:
    """
    Получение всех абонементов с автопродлением, которые заканчиваются сегодня (для обратной совместимости)
    """
    return get_auto_renewal_subscriptions(db, days_back=0)


def transfer_sessions(
    db: Session,
    old_subscription: StudentSubscription,
    new_subscription: StudentSubscription,
    max_sessions: int = 3
) -> int:
    """
    Переносит неиспользованные занятия из старой подписки в новую.
    Возвращает количество перенесённых занятий.
    """
    # Перенести занятия (максимум max_sessions)
    transferred = min(old_subscription.sessions_left, max_sessions)
    
    # Обнуляем старую подписку
    old_subscription.sessions_left = 0
    old_subscription.transferred_sessions = 0
    
    # Добавляем занятия в новую подписку
    new_subscription.sessions_left += transferred
    new_subscription.transferred_sessions = transferred
    
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объекты, но не коммитим
    db.refresh(old_subscription)
    db.refresh(new_subscription)
    
    return transferred


