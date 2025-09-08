from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import TrainerCreate, TrainerResponse, TrainerUpdate, TrainersList, UserRole, StatusUpdate
from app.schemas.payment import PaymentResponse, PaymentHistoryFilterRequest, PaymentHistoryListResponse, PaymentListResponse, PaymentExtendedListResponse
from app.crud.trainer import (create_trainer, get_trainer, get_all_trainers,
                              update_trainer, delete_trainer, update_trainer_status)
from app.services.financial import FinancialService

router = APIRouter(prefix="/trainers", tags=["Trainers"])


# Создание тренера
@router.post("/", response_model=TrainerResponse)
def create_trainer_endpoint(trainer_data: TrainerCreate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return create_trainer(db, trainer_data)


# Получение всех тренеров
@router.get("/", response_model=TrainersList)
def get_trainers_endpoint(current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainers = get_all_trainers(db)
    return TrainersList(trainers=trainers)


# Получение тренера по ID
@router.get("/{trainer_id}", response_model=TrainerResponse)
def get_trainer_endpoint(trainer_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = get_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    return trainer


# Обновление тренера
@router.patch("/{trainer_id}", response_model=TrainerResponse)
def update_trainer_endpoint(trainer_id: int, trainer_data: TrainerUpdate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = update_trainer(db, trainer_id, trainer_data)
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    return trainer


# Удаление тренера
@router.delete("/{trainer_id}")
def delete_trainer_endpoint(trainer_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    success = delete_trainer(db, trainer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    return {"message": "Trainer deleted successfully"}


# Обновление статуса тренера
@router.patch("/{trainer_id}/status", response_model=TrainerResponse)
def update_trainer_status_endpoint(trainer_id: int, status_data: StatusUpdate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = update_trainer_status(db, trainer_id, status_data.is_active)
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    return trainer


# Получение платежей тренера
@router.get("/{trainer_id}/payments", response_model=PaymentHistoryListResponse)
def get_trainer_payments_endpoint(
    trainer_id: int,
    period: str = Query("all", description="Период: week/2weeks/all"),
    client_id: Optional[int] = Query(None, description="ID клиента для фильтрации"),
    amount_min: Optional[float] = Query(None, description="Минимальная сумма"),
    amount_max: Optional[float] = Query(None, description="Максимальная сумма"),
    date_from: Optional[str] = Query(None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания периода (YYYY-MM-DD)"),
    description_search: Optional[str] = Query(None, description="Поиск по описанию"),
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(50, description="Максимальное количество записей"),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение платежей конкретного тренера с фильтрацией и пагинацией.
    Только для админов.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Проверяем существование тренера
    trainer = get_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    
    # Создаем объект фильтров
    filters = PaymentHistoryFilterRequest(
        created_by_id=trainer_id,  # Фильтруем по создателю (тренеру)
        client_id=client_id,
        amount_min=amount_min,
        amount_max=amount_max,
        date_from=date_from,
        date_to=date_to,
        description_search=description_search,
        skip=skip,
        limit=limit
    )
    
    # Добавляем логику для периода, если указан
    if period != "all":
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if period == "week":
            filters.date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        elif period == "2weeks":
            filters.date_from = (today - timedelta(days=14)).strftime("%Y-%m-%d")

    
    service = FinancialService(db)
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

# Получение платежей, зарегистрированных тренером
@router.get("/{trainer_id}/registered-payments", response_model=PaymentExtendedListResponse)
def get_trainer_registered_payments_endpoint(
    trainer_id: int,
    period: str = Query("all", description="Период: week/2weeks/all"),
    client_id: Optional[int] = Query(None, description="ID клиента для фильтрации"),
    amount_min: Optional[float] = Query(None, description="Минимальная сумма"),
    amount_max: Optional[float] = Query(None, description="Максимальная сумма"),
    date_from: Optional[str] = Query(None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания периода (YYYY-MM-DD)"),
    description_search: Optional[str] = Query(None, description="Поиск по описанию"),
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(50, description="Максимальное количество записей"),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение платежей, зарегистрированных конкретным тренером.
    Доступно для админов и самого тренера.
    """
    # Проверяем права доступа
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Тренер может смотреть только свои платежи
    if current_user["role"] == UserRole.TRAINER and current_user["id"] != trainer_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Проверяем существование тренера
    trainer = get_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    
    service = FinancialService(db)
    result = service.get_trainer_registered_payments(
        trainer_id=trainer_id,
        period=period,
        client_id=client_id,
        amount_min=amount_min,
        amount_max=amount_max,
        date_from=date_from,
        date_to=date_to,
        description_search=description_search,
        skip=skip,
        limit=limit
    )
    
    return PaymentExtendedListResponse(
        payments=result["payments"],
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"],
        has_more=result["has_more"]
    )