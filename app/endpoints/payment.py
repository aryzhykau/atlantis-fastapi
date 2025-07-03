from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.payment import PaymentCreate, PaymentResponse, ClientBalanceResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse)
def create_payment(
    payment: PaymentCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Регистрация нового платежа.
    Только для админов и тренеров.
    """
    service = PaymentService(db)
    return service.register_payment(
        client_id=payment.client_id,
        amount=payment.amount,
        registered_by_id=current_user["id"],
        description=payment.description
    )


@router.delete("/{payment_id}", response_model=PaymentResponse)
def cancel_payment(
    payment_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Отмена платежа.
    Только для админов.
    """
    service = PaymentService(db)
    return service.cancel_payment(
        payment_id=payment_id,
        cancelled_by_id=current_user["id"]
    )


@router.get("/client/{client_id}", response_model=List[PaymentResponse])
def get_client_payments(
    client_id: int,
    cancelled_status: str = "all",
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка платежей клиента.
    Доступно админам и тренерам.
    
    Args:
        client_id: ID клиента
        cancelled_status: Статус отмены платежей:
            - "all": все платежи (по умолчанию)
            - "cancelled": только отмененные платежи
            - "not_cancelled": только неотмененные платежи
        skip: Смещение для пагинации
        limit: Лимит записей для пагинации
    """
    service = PaymentService(db)
    service.validate_admin_or_trainer(current_user["id"])
    return service.get_client_payments(
        client_id=client_id,
        cancelled_status=cancelled_status,
        skip=skip,
        limit=limit
    )


@router.get("/client/{client_id}/balance", response_model=ClientBalanceResponse)
def get_client_balance(
    client_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение текущего баланса клиента.
    Доступно админам и тренерам.
    """
    service = PaymentService(db)
    service.validate_admin_or_trainer(current_user["id"])
    balance = service.get_client_balance(client_id)
    return ClientBalanceResponse(client_id=client_id, balance=balance)


@router.get("/filtered", response_model=List[PaymentResponse])
def get_filtered_payments(
    registered_by_me: bool = Query(False, description="Только платежи текущего пользователя"),
    period: str = Query("week", description="Период: week/month/3months"),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка платежей с фильтрацией.
    Доступно админам и тренерам.
    
    Args:
        registered_by_me: Если True, возвращает только платежи зарегистрированные текущим пользователем
        period: Период для фильтрации (week/month/3months)
    """
    service = PaymentService(db)
    service.validate_admin_or_trainer(current_user["id"])
    return service.get_payments_with_filters(
        user_id=current_user["id"],
        registered_by_me=registered_by_me,
        period=period
    ) 