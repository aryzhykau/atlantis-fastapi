from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.payment import (
    PaymentCreate, 
    PaymentResponse, 
    PaymentExtendedResponse,
    ClientBalanceResponse,
    PaymentHistoryFilterRequest,
    PaymentHistoryListResponse
)
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


@router.get("/filtered", response_model=List[PaymentExtendedResponse])
def get_filtered_payments(
    registered_by_me: bool = Query(False, description="Только платежи текущего пользователя"),
    period: str = Query("week", description="Период: week/2weeks"),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка платежей с фильтрацией.
    Доступно админам и тренерам.
    
    Args:
        registered_by_me: Если True, возвращает только платежи зарегистрированные текущим пользователем
        period: Период для фильтрации (week/2weeks)
    """
    service = PaymentService(db)
    service.validate_admin_or_trainer(current_user["id"])
    return service.get_payments_with_filters_extended(
        user_id=current_user["id"],
        registered_by_me=registered_by_me,
        period=period
    )


@router.get("/history", response_model=PaymentHistoryListResponse)
def get_payment_history(
    operation_type: str = Query(None, description="Тип операции"),
    client_id: int = Query(None, description="ID клиента"),
    created_by_id: int = Query(None, description="ID создателя операции"),
    date_from: str = Query(None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: str = Query(None, description="Дата окончания периода (YYYY-MM-DD)"),
    amount_min: float = Query(None, description="Минимальная сумма"),
    amount_max: float = Query(None, description="Максимальная сумма"),
    description_search: str = Query(None, description="Поиск по описанию"),
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение истории всех транзакций с фильтрами и пагинацией.
    Только для админов.
    """
    # Создаем объект фильтров из query параметров
    filters = PaymentHistoryFilterRequest(
        operation_type=operation_type,
        client_id=client_id,
        created_by_id=created_by_id,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        description_search=description_search,
        skip=skip,
        limit=limit
    )
    
    service = PaymentService(db)
    result = service.get_payment_history_with_filters(
        user_id=current_user["id"],
        filters=filters
    )
    
    return PaymentHistoryListResponse(
        items=result["items"],
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"],
        has_more=result["has_more"]
    ) 