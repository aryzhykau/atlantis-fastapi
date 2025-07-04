from datetime import datetime, timedelta
from typing import Optional, List, Literal, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, and_, func, or_

from app.models import Payment, PaymentHistory, User, Invoice
from app.models.user import User as User2
from app.models.payment_history import OperationType
from app.schemas.payment import PaymentCreate, PaymentHistoryFilterRequest


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


def get_payment_history_filtered(
    db: Session,
    filters: PaymentHistoryFilterRequest
) -> Tuple[List[dict], int]:
    """
    Получение истории платежей с фильтрами и пагинацией (через relationships)
    """
    query = db.query(PaymentHistory)

    # Фильтры
    if filters.operation_type:
        query = query.filter(PaymentHistory.operation_type == filters.operation_type)
    if filters.client_id:
        query = query.filter(PaymentHistory.client_id == filters.client_id)
    if filters.created_by_id:
        query = query.filter(PaymentHistory.created_by_id == filters.created_by_id)
    if filters.date_from:
        query = query.filter(PaymentHistory.created_at >= filters.date_from)
    if filters.date_to:
        query = query.filter(PaymentHistory.created_at <= filters.date_to)
    if filters.amount_min is not None:
        query = query.filter(PaymentHistory.amount >= filters.amount_min)
    if filters.amount_max is not None:
        query = query.filter(PaymentHistory.amount <= filters.amount_max)
    if filters.description_search:
        search_term = f"%{filters.description_search}%"
        query = query.filter(
            or_(
                PaymentHistory.description.ilike(search_term),
                PaymentHistory.payment.has(Payment.description.ilike(search_term))
            )
        )

    total_count = query.count()

    # Сортировка и пагинация
    query = query.order_by(desc(PaymentHistory.created_at))
    query = query.offset(filters.skip).limit(filters.limit)

    # Жадная загрузка связанных объектов
    query = query.options(
        selectinload(PaymentHistory.client),
        selectinload(PaymentHistory.created_by),
        selectinload(PaymentHistory.payment),
        selectinload(PaymentHistory.invoice)
    )

    results = query.all()
    history_items = []
    for ph in results:
        item = {
            'id': ph.id,
            'client_id': ph.client_id,
            'payment_id': ph.payment_id,
            'invoice_id': ph.invoice_id,
            'operation_type': ph.operation_type,
            'amount': ph.amount if ph.amount is not None else 0.0,
            'balance_before': ph.balance_before if ph.balance_before is not None else 0.0,
            'balance_after': ph.balance_after if ph.balance_after is not None else 0.0,
            'description': ph.description,
            'created_at': ph.created_at,
            'created_by_id': ph.created_by_id,
            # Связанные данные
            'client_first_name': ph.client.first_name if ph.client else None,
            'client_last_name': ph.client.last_name if ph.client else None,
            'created_by_first_name': ph.created_by.first_name if ph.created_by else None,
            'created_by_last_name': ph.created_by.last_name if ph.created_by else None,
            'payment_description': ph.payment.description if ph.payment else None,
        }
        history_items.append(item)
    return history_items, total_count
