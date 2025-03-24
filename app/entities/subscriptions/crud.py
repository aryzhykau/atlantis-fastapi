import datetime
import logging

from sqlalchemy.orm import Session
from app.entities.subscriptions.models import Subscription
from app.entities.subscriptions.schemas import SubscriptionCreate, SubscriptionRead

logger = logging.getLogger(__name__)

def create_subscription(db: Session, subscription: SubscriptionCreate):
    try:
        new_subscription = subscription.model_dump()
        new_subscription["created_at"] = new_subscription["updated_at"]  = datetime.datetime.now()
        db_subscription = Subscription(**new_subscription)
        db.add(db_subscription)
        db.commit()
        db.refresh(db_subscription)
        return db_subscription
    except Exception as e:
        db.rollback()
        raise e

def get_subscription_by_id(db: Session, subscription_id: int):
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()


def get_training_types(db: Session):
    subscriptions = db.query(Subscription).order_by(Subscription.title).all()
    logger.debug(f"TRAINING TYPES = {subscriptions}")
    return [SubscriptionRead.model_validate(subscription) for subscription in subscriptions] if subscriptions else []
