from datetime import datetime, timedelta
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models import Payment, PaymentHistory, User
from app.models.payment_history import OperationType
from app.schemas.payment import PaymentCreate


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


def get_payments(db: Session, skip: int = 0, limit: int = 100) -> List[Payment]:
    return db.query(Payment).offset(skip).limit(limit).all()


def get_payments_with_filters(
    db: Session,
    user_id: int,
    registered_by_me: bool = False,
    period: str = "week"
) -> List[Payment]:
    """
    Получение платежей с фильтрацией по регистрировавшему и периоду
    
    Args:
        db: Database session
        user_id: ID пользователя (тренера/админа)
        registered_by_me: Если True, возвращает только платежи зарегистрированные этим пользователем
        period: Период для фильтрации (week/month/3months)
    """
    # Вычисляем дату начала периода
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "3months":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=7)  # По умолчанию неделя
    
    # Базовый запрос
    query = db.query(Payment).filter(
        Payment.payment_date >= start_date
    )
    
    # Фильтрация по регистрировавшему
    if registered_by_me:
        query = query.filter(Payment.registered_by_id == user_id)
    
    # Исключаем отменённые платежи
    query = query.filter(Payment.cancelled_at.is_(None))
    
    # Сортировка по дате создания (новые сначала)
    return query.order_by(desc(Payment.payment_date)).all()
