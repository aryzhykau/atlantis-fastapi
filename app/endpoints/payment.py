import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.payment import (
    PaymentCreate, 
    PaymentResponse, 
    PaymentExtendedResponse,
    ClientBalanceResponse,
    PaymentHistoryFilterRequest,
    PaymentHistoryListResponse
)
from app.services.financial import FinancialService
from app.crud import payment as crud_payment
from app.crud import user as crud_user
from app.errors.payment_errors import PaymentError, PaymentNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse)
def create_payment(
    payment: PaymentCreate,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Регистрация нового платежа.
    Доступно админам и тренерам.
    """
    service = FinancialService(db)
    try:
        return service.register_standalone_payment(
            client_id=payment.client_id,
            amount=payment.amount,
            registered_by_id=current_user["id"],
            description=payment.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filtered", response_model=List[PaymentExtendedResponse])
def get_filtered_payments(
    registered_by_me: Optional[bool] = Query(None, description="Только платежи текущего пользователя"),
    period: str = Query("week", description="Период: week/2weeks"),
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение списка платежей с фильтрацией.
    Доступно админам и тренерам.
    
    Args:
        registered_by_me: Если "true", возвращает только платежи зарегистрированные текущим пользователем
        period: Период для фильтрации (week/2weeks)
    """
    
    # This logic should be moved to a service if it involves complex business rules
    # For now, keeping it as is, but it's a candidate for refactoring.
    service = FinancialService(db)
    # service.validate_admin_or_trainer(current_user["id"]) # Validation should be handled by service or dependency
    return service.get_filtered_payments(
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
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение истории всех транзакций с фильтрами и пагинацией.
    Для админов и владельцев.
    """
    # This logic should be moved to a service if it involves complex business rules
    # For now, keeping it as is, but it's a candidate for refactoring.
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
    
    service = FinancialService(db)
    result = service.get_payment_history(
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


@router.delete("/{payment_id}", response_model=PaymentResponse)
def cancel_payment(
    payment_id: int,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Отмена платежа.
    Для админов и владельцев.
    """
    service = FinancialService(db)
    try:
        return service.cancel_standalone_payment(
            payment_id=payment_id,
            cancelled_by_id=current_user["id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PaymentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение платежа по ID.
    Доступно админам, тренерам и владельцам.
    """
    # Direct CRUD call as no business logic is involved
    payment = crud_payment.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение списка всех платежей.
    Доступно админам, тренерам и владельцам.
    """
    # Direct CRUD call as no business logic is involved
    return crud_payment.get_payments(db, skip=skip, limit=limit)


@router.get("/client/{client_id}", response_model=List[PaymentResponse])
def get_client_payments(
    client_id: int,
    cancelled_status: str = "all",
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение списка платежей клиента.
    Доступно админам, тренерам и владельцам.
    
    Args:
        client_id: ID клиента
        cancelled_status: Статус отмены платежей:
            - "all": все платежи (по умолчанию)
            - "cancelled": только отмененные платежи
            - "not_cancelled": только неотмененные платежи
        skip: Смещение для пагинации
        limit: Лимит записей для пагинации
    """
    # Direct CRUD call as no business logic is involved
    return crud_payment.get_client_payments(
        db,
        client_id=client_id,
        cancelled_status=cancelled_status,
        skip=skip,
        limit=limit
    )


@router.get("/client/{client_id}/balance", response_model=ClientBalanceResponse)
def get_client_balance(
    client_id: int,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Получение текущего баланса клиента.
    Доступно админам, тренерам и владельцам.
    """
    # Direct CRUD call as no business logic is involved
    user = crud_user.get_user_by_id(db, client_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientBalanceResponse(client_id=client_id, balance=user.balance)