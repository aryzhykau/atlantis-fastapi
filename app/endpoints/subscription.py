import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionList,
    StudentSubscriptionCreate,
    StudentSubscriptionResponse,
    StudentSubscriptionUpdate
)
from app.crud.subscription import (
    create_subscription,
    get_subscriptions,
    get_subscription_by_id,
    update_subscription,
)
from app.schemas.user import UserRole
from app.services.subscription import SubscriptionService

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
@router.get("/", response_model=SubscriptionList)
def get_subscriptions_endpoint(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    subscriptions = get_subscriptions(db)
    return SubscriptionList(items=subscriptions, total=len(subscriptions))


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
    """
    Обновление существующего абонемента.
    Только для админов.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update subscriptions")
    
    subscription = get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    updated_subscription = update_subscription(db, subscription_id, subscription_data)
    return updated_subscription


@router.post("/student", response_model=StudentSubscriptionResponse)
def add_subscription_to_student(
    student_subscription: StudentSubscriptionCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Добавление абонемента студенту.
    Только для админов и тренеров.
    """
    
    service = SubscriptionService(db)
    return service.add_subscription_to_student(
        student_id=student_subscription.student_id,
        subscription_id=student_subscription.subscription_id,
        is_auto_renew=student_subscription.is_auto_renew,
        created_by_id=current_user["id"]
    )


@router.get("/student/{student_id}", response_model=List[StudentSubscriptionResponse])
def get_student_subscriptions(
    student_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка абонементов студента.
    Доступно всем авторизованным пользователям.
    """
    service = SubscriptionService(db)
    return service.get_active_student_subscriptions(student_id)


@router.patch("/student/{subscription_id}/auto-renewal", response_model=StudentSubscriptionResponse)
def update_auto_renewal(
    subscription_id: int,
    update: StudentSubscriptionUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Обновление статуса автопродления.
    Только для админов и тренеров.
    """
    service = SubscriptionService(db)
    return service.update_auto_renewal(
        student_subscription_id=subscription_id,
        is_auto_renew=update.is_auto_renew,
        updated_by_id=current_user.id
    )


@router.post("/student/{subscription_id}/freeze", response_model=StudentSubscriptionResponse)
def freeze_subscription(
    subscription_id: int,
    freeze_start_date: datetime,
    freeze_duration_days: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Заморозка абонемента.
    Только для админов и тренеров.
    """
    service = SubscriptionService(db)
    return service.freeze_subscription(
        student_subscription_id=subscription_id,
        freeze_start_date=freeze_start_date,
        freeze_duration_days=freeze_duration_days,
        updated_by_id=current_user.id
    )


@router.post("/student/{subscription_id}/unfreeze", response_model=StudentSubscriptionResponse)
def unfreeze_subscription(
    subscription_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Разморозка абонемента.
    Только для админов и тренеров.
    """
    service = SubscriptionService(db)
    return service.unfreeze_subscription(
        student_subscription_id=subscription_id,
        updated_by_id=current_user.id
    )
