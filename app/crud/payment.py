from datetime import datetime
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Payment, PaymentHistory, User
from app.models.payment_history import OperationType


def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    """Получение платежа по ID"""
    return db.query(Payment).filter(Payment.id == payment_id).first()


def get_client_payments(
    db: Session,
    client_id: int,
    cancelled_status: Literal["all", "cancelled", "not_cancelled"] = "all",
    skip: int = 0,
    limit: int = 100
) -> List[Payment]:
    """
    Получение списка платежей клиента
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        cancelled_status: Статус отмены платежей для фильтрации:
            - "all": все платежи (по умолчанию)
            - "cancelled": только отмененные платежи
            - "not_cancelled": только неотмененные платежи
        skip: Количество записей для пропуска (для пагинации)
        limit: Максимальное количество возвращаемых записей
        
    Returns:
        Список платежей, соответствующих заданным критериям
    """
    query = db.query(Payment).filter(Payment.client_id == client_id)
    
    # Применяем фильтр по статусу отмены
    if cancelled_status == "cancelled":
        query = query.filter(Payment.cancelled_at.isnot(None))
    elif cancelled_status == "not_cancelled":
        query = query.filter(Payment.cancelled_at.is_(None))
    
    # Сортировка, пагинация и выполнение запроса
    return (
        query
        .order_by(desc(Payment.payment_date))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_payment(
    db: Session,
    client_id: int,
    amount: float,
    registered_by_id: int,
    description: Optional[str] = None
) -> Payment:
    """Создание нового платежа"""
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise ValueError("Client not found")

    payment = Payment(
        client_id=client_id,
        amount=amount,
        description=description,
        registered_by_id=registered_by_id,
        payment_date=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
