import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionsList,
)
from app.crud.subscription import (
    create_subscription,
    get_subscriptions,
    get_subscription_by_id,
    update_subscription,
)
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# Создание нового абонемента
@router.post("/", response_model=SubscriptionResponse)
def create_subscription_endpoint(
        subscription_data: SubscriptionCreate,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    new_subscription = create_subscription(db, subscription_data)
    return new_subscription


# Получение списка всех абонементов
@router.get("/", response_model=SubscriptionsList)
def get_subscriptions_endpoint(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    subscriptions = get_subscriptions(db)
    return SubscriptionsList(subscriptions=subscriptions)


# Получение абонемента по ID
@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription_endpoint(
        subscription_id: int,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    subscription = get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


# Обновление существующего абонемента
@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription_endpoint(
        subscription_id: int,
        subscription_data: SubscriptionUpdate,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    updated_subscription = update_subscription(db, subscription_id, subscription_data)
    if not updated_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated_subscription
