"""Эндпоинты v2 для абонементов."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.database import transactional
from app.schemas.subscription_v2 import (
    StudentSubscriptionCreateV2,
    StudentSubscriptionResponseV2,
    StudentSubscriptionListV2,
)
from app.services.subscription_v2 import add_subscription_to_student_v2
from app.crud import subscription as crud_subscription
from app.models import StudentSubscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/subscriptions", tags=["Subscriptions v2"])


@router.post("/student", response_model=StudentSubscriptionResponseV2)
def add_subscription_to_student_v2_endpoint(
    data: StudentSubscriptionCreateV2,
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Назначить абонемент студенту (v2 логика: пропорциональная цена, PENDING инвойс)."""
    try:
        with transactional(db):
            sub = add_subscription_to_student_v2(
                db,
                student_id=data.student_id,
                subscription_id=data.subscription_id,
                is_auto_renew=data.is_auto_renew,
            )
        db.refresh(sub)
        # Подтягиваем sessions_per_week из шаблона
        result = StudentSubscriptionResponseV2.model_validate(sub)
        result.sessions_per_week = sub.subscription.sessions_per_week if sub.subscription else None
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding subscription v2: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}", response_model=StudentSubscriptionListV2)
def get_student_subscriptions_v2_endpoint(
    student_id: int,
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Список абонементов студента с полями v2."""
    subs = crud_subscription.get_student_subscriptions(db, student_id=student_id)
    items = []
    for sub in subs:
        item = StudentSubscriptionResponseV2.model_validate(sub)
        item.sessions_per_week = sub.subscription.sessions_per_week if sub.subscription else None
        items.append(item)
    return StudentSubscriptionListV2(items=items, total=len(items))
