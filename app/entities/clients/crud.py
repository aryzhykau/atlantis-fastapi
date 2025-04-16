import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.entities.clients.models import Client, ClientSubscription
from app.entities.subscriptions.models import Subscription
from app.entities.users.models import User
from app.entities.users.schemas import ClientCreate, ClientSubscriptionCreate


logger = logging.getLogger(__name__)


def create_client(db, user_id: int, client: ClientCreate):
    new_client = client.model_dump()
    new_client["created_at"] = new_client["updated_at"] = datetime.now()
    new_client["user_id"] = user_id
    db_client = Client(**new_client)
    db.add(db_client)



def create_client_subscription(db: Session, client_id: int, client_subscription_data: ClientSubscriptionCreate):
    client = db.query(User).filter(User.id == client_id).first()

    subscription = db.query(Subscription).filter(Subscription.id == client_subscription_data.subscription_id).first()
    if not client or not subscription:
        return None

    client_subscription = ClientSubscription(
        client_id=client_id,
        subscription_id = client_subscription_data.subscription_id,
        start_date = client_subscription_data.start_date,
        end_date=client_subscription_data.start_date + timedelta(days=subscription.duration),
        active=client_subscription_data.active,
        sessions_left=subscription.total_sessions,
    )

    db.add(client_subscription)
    db.commit()
    db.refresh(client_subscription)
    return client_subscription