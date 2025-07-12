from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Subscription, StudentSubscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.schemas.student_subscription import StudentSubscriptionCreate, StudentSubscriptionUpdate


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
    query = db.query(StudentSubscription).filter(
        StudentSubscription.student_id == student_id
    )
    
    if status:
        query = query.filter(StudentSubscription.status == status)
    if not include_expired:
        query = query.filter(StudentSubscription.end_date >= date.today())
        
    return query.order_by(StudentSubscription.start_date.desc()).all()


def get_student_subscriptions_by_status(
    db: Session,
    student_id: int,
    status: str,
) -> List[StudentSubscription]:
    """
    Получение абонементов студента по статусу
    """
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.student_id == student_id,
            StudentSubscription.status == status
        )
    ).order_by(StudentSubscription.start_date.desc()).all()


def get_active_subscription(
    db: Session,
    student_id: int,
    training_date: date,
) -> Optional[StudentSubscription]:
    """
    Получение активного абонемента студента на дату тренировки
    """
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.student_id == student_id,
            StudentSubscription.status == 'active',
            StudentSubscription.start_date <= training_date,
            StudentSubscription.end_date >= training_date,
            StudentSubscription.sessions_left > 0,
            # Проверяем, что абонемент не заморожен на дату тренировки
            or_(
                StudentSubscription.freeze_start_date.is_(None),
                and_(
                    StudentSubscription.freeze_start_date.isnot(None),
                    StudentSubscription.freeze_end_date.isnot(None),
                    or_(
                        StudentSubscription.freeze_start_date > training_date,
                        StudentSubscription.freeze_end_date < training_date
                    )
                )
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
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc)
    return (
        db.query(StudentSubscription)
        .filter(
            and_(
                StudentSubscription.student_id == student_id,
                StudentSubscription.start_date <= today,
                StudentSubscription.end_date >= today,
                ~StudentSubscription.status.in_(["expired", "frozen"])
            )
        )
        .all()
    )


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
        status=subscription_data.status,
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


def freeze_subscription(
    db: Session,
    student_subscription_id: int,
    freeze_start_date: date,
    freeze_end_date: date,
) -> Optional[StudentSubscription]:
    """
    Заморозка абонемента
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    student_subscription.freeze_start_date = freeze_start_date
    student_subscription.freeze_end_date = freeze_end_date
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_subscription)
    return student_subscription


def unfreeze_subscription(
    db: Session,
    student_subscription_id: int,
) -> Optional[StudentSubscription]:
    """
    Разморозка абонемента
    """
    student_subscription = get_student_subscription(db, student_subscription_id)
    if not student_subscription:
        return None

    student_subscription.freeze_start_date = None
    student_subscription.freeze_end_date = None
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
    expiry_date = date.today() + timedelta(days=days_before_expiry)
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.status == 'active',
            StudentSubscription.end_date <= expiry_date,
            StudentSubscription.end_date >= date.today(),
        )
    ).all()


def get_frozen_subscriptions(
    db: Session,
    current_date: Optional[date] = None,
) -> List[StudentSubscription]:
    """
    Получение замороженных абонементов, у которых истек срок заморозки
    """
    if current_date is None:
        current_date = date.today()
        
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
    start_date: datetime,
    end_date: datetime,
) -> List[StudentSubscription]:
    """
    Получение всех активных абонементов с автопродлением, которые заканчиваются в указанный период
    """
    return db.query(StudentSubscription).filter(
        and_(
            StudentSubscription.is_auto_renew == True,
            StudentSubscription.status == "active",
            StudentSubscription.end_date >= start_date,
            StudentSubscription.end_date < end_date,
            StudentSubscription.auto_renewal_invoice_id.is_(None)  # Защита от дублей
        )
    ).all()

