import logging
from datetime import datetime
from typing import List, Optional

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
    StudentSubscriptionUpdate,
    SubscriptionFreeze
)

from app.schemas.user import UserRole
from app.services.subscription import SubscriptionService
from app.crud import subscription as crud_subscription # Import crud for direct calls
from app.errors.subscription_errors import (
    SubscriptionError,
    SubscriptionNotFound,
    SubscriptionNotActive,
    SubscriptionAlreadyFrozen,
    SubscriptionNotFrozen
)

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
    service = SubscriptionService(db)
    try:
        return service.create_subscription(subscription_data)
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Получение списка всех абонементов
@router.get("/", response_model=SubscriptionList)
def get_subscriptions_endpoint(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Direct CRUD call as no business logic is involved
    subscriptions = crud_subscription.get_subscriptions(db)
    return SubscriptionList(items=subscriptions, total=len(subscriptions))


# Получение абонемента по ID
@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription_endpoint(
        subscription_id: int,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Direct CRUD call as no business logic is involved
    subscription = crud_subscription.get_subscription_by_id(db, subscription_id)
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
    
    service = SubscriptionService(db)
    try:
        updated_subscription = service.update_subscription(subscription_id, subscription_data)
        if not updated_subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return updated_subscription
    except SubscriptionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        return service.add_subscription_to_student(
            student_id=student_subscription.student_id,
            subscription_id=student_subscription.subscription_id,
            is_auto_renew=student_subscription.is_auto_renew,
            created_by_id=current_user["id"]
        )
    except SubscriptionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SubscriptionNotActive as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}", response_model=List[StudentSubscriptionResponse])
def get_student_subscriptions(
    student_id: int,
    status: Optional[str] = None,
    include_expired: bool = True,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка абонементов студента.
    Доступно всем авторизованным пользователям.
    
    Args:
        student_id: ID студента
        status: Фильтр по статусу ("active", "pending", "frozen", "expired")
        include_expired: Включать ли истекшие абонементы (по умолчанию True для истории)
    """
    # Use the full subscription function to get history
    return crud_subscription.get_student_subscriptions(
        db, 
        student_id, 
        status=status, 
        include_expired=include_expired
    )


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
    try:
        return service.update_auto_renewal(
            student_subscription_id=subscription_id,
            is_auto_renew=update.is_auto_renew,
            updated_by_id=current_user["id"]
        )
    except SubscriptionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/student/{subscription_id}/freeze", response_model=StudentSubscriptionResponse)
def freeze_subscription(
    subscription_id: int,
    freeze_data: SubscriptionFreeze,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Заморозка абонемента.
    Только для админов и тренеров.
    """
    service = SubscriptionService(db)
    try:
        return service.freeze_subscription(
            student_subscription_id=subscription_id,
            freeze_start_date=freeze_data.freeze_start_date,
            freeze_duration_days=freeze_data.freeze_duration_days,
            updated_by_id=current_user["id"]
        )
    except SubscriptionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SubscriptionNotActive as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SubscriptionAlreadyFrozen as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        return service.unfreeze_subscription(
            student_subscription_id=subscription_id,
            updated_by_id=current_user["id"]
        )
    except SubscriptionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SubscriptionNotFrozen as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/process-auto-renewals")
def process_auto_renewals_endpoint(
    days_back: int = 7,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Manually trigger auto-renewal processing for subscriptions.
    Processes subscriptions that ended today or in the past X days.
    Only for admins.
    
    Args:
        days_back: How many days back to look for expired subscriptions (default: 7, max: 30)
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can trigger auto-renewals")
    
    # Limit the lookback period for safety
    if days_back > 30:
        raise HTTPException(status_code=400, detail="Cannot look back more than 30 days")
    
    service = SubscriptionService(db)
    try:
        renewed_subscriptions = service.process_auto_renewals(days_back=days_back)
        return {
            "message": f"Successfully processed auto-renewals",
            "days_back": days_back,
            "renewals_processed": len(renewed_subscriptions),
            "subscription_ids": [sub.id for sub in renewed_subscriptions]
        }
    except SubscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))