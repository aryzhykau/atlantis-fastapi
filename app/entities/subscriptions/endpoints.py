from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.entities.subscriptions.crud import (
    create_subscription,
    get_subscription_by_id,
    get_subscriptions  # Убедитесь, что функция в crud.py называется get_subscriptions
)
from app.entities.subscriptions.schemas import SubscriptionCreate, SubscriptionRead
from app.entities.users.models import UserRoleEnum

subscriptions_router = APIRouter()


@subscriptions_router.post("/", response_model=SubscriptionRead, status_code=201)
async def add_subscription(
        subscription: SubscriptionCreate,
        db: Session = Depends(get_db),
        current_user=Depends(verify_jwt_token),
):
    if current_user["role"] == UserRoleEnum.ADMIN:
        return create_subscription(db, subscription)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@subscriptions_router.put("/{subscription_id}", response_model=SubscriptionRead)
async def update_subscription(
        subscription_id: int,
        subscription: SubscriptionCreate,
        db: Session = Depends(get_db),
        current_user=Depends(verify_jwt_token),
):
    if current_user["role"] == UserRoleEnum.ADMIN:
        existing_subscription = get_subscription_by_id(db, subscription_id)
        if not existing_subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Update subscription details
        for key, value in subscription.dict().items():
            setattr(existing_subscription, key, value)
        existing_subscription.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing_subscription)
        return existing_subscription
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@subscriptions_router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
        subscription_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(verify_jwt_token),
):
    if current_user["role"] == UserRoleEnum.ADMIN:
        subscription = get_subscription_by_id(db, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        db.delete(subscription)
        db.commit()

@subscriptions_router.get("/{subscription_id}", response_model=SubscriptionRead)
async def read_subscription(
        subscription_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(verify_jwt_token),
):
    if current_user["role"] == UserRoleEnum.ADMIN:
        subscription = get_subscription_by_id(db, subscription_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@subscriptions_router.get("/", response_model=list[SubscriptionRead])
async def read_subscriptions(
        db: Session = Depends(get_db),
        current_user=Depends(verify_jwt_token),
):
    if current_user["role"] == UserRoleEnum.ADMIN:
        subscriptions = get_subscriptions(db)
        return subscriptions
    else:
        raise HTTPException(status_code=403, detail="Forbidden")
    
