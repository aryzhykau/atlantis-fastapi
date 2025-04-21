from sqlalchemy.orm import Session
from ..models import Subscription
from ..schemas.subscription import SubscriptionCreate, SubscriptionUpdate


# Получение списка всех абонементов
def get_subscriptions(db: Session):
    return db.query(Subscription).all()


# Получение конкретного абонемента по ID
def get_subscription_by_id(db: Session, subscription_id: int):
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()


# Создание нового абонемента
def create_subscription(db: Session, subscription: SubscriptionCreate):
    db_subscription = Subscription(
        name=subscription.name,
        price=subscription.price,
        number_of_sessions=subscription.number_of_sessions,
        validity_days=subscription.validity_days,
        is_active=subscription.is_active,
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


# Обновление существующего абонемента
def update_subscription(db: Session, subscription_id: int, updated_data: SubscriptionUpdate):
    db_subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if db_subscription:
        for key, value in updated_data.model_dump(exclude_unset=True).items():
            setattr(db_subscription, key, value)
        db.commit()
        db.refresh(db_subscription)
    return db_subscription

