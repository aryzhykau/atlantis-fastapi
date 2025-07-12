from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ С ПЛАТЕЖАМИ
# =============================================================================

def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    """
    Получение платежа по ID
    """
    return db.query(Payment).filter(Payment.id == payment_id).first()


def get_payments(
    db: Session,
    *,
    client_id: Optional[int] = None,
    registered_by_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Payment]:
    """
    Получение списка платежей с фильтрами
    """
    query = db.query(Payment)
    
    if client_id:
        query = query.filter(Payment.client_id == client_id)
    if registered_by_id:
        query = query.filter(Payment.registered_by_id == registered_by_id)
        
    return query.order_by(desc(Payment.payment_date)).offset(skip).limit(limit).all()


def get_client_payments(
    db: Session,
    client_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Payment]:
    """
    Получение платежей клиента
    """
    return get_payments(db, client_id=client_id, skip=skip, limit=limit)


def create_payment(db: Session, payment_data: PaymentCreate) -> Payment:
    """
    Создание нового платежа
    """
    db_payment = Payment(
        client_id=payment_data.client_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        description=payment_data.description,
        payment_date=payment_data.payment_date or datetime.now(timezone.utc),
        created_by_id=payment_data.created_by_id,
    )
    db.add(db_payment)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(db_payment)
    return db_payment


def update_payment(
    db: Session,
    payment_id: int,
    update_data: PaymentUpdate,
) -> Optional[Payment]:
    """
    Обновление платежа
    """
    payment = get_payment(db, payment_id)
    if not payment:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(payment, field, value)

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(payment)
    return payment


def cancel_payment(
    db: Session,
    payment_id: int,
    cancelled_by_id: Optional[int] = None,
) -> Optional[Payment]:
    """
    Отмена платежа
    """
    payment = get_payment(db, payment_id)
    if not payment:
        return None

    if payment.cancelled_at:
        return payment  # Уже отменён

    payment.cancelled_at = datetime.now(timezone.utc)
    payment.cancelled_by_id = cancelled_by_id

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(payment)
    return payment


def get_payment_count(
    db: Session,
    *,
    client_id: Optional[int] = None,
    registered_by_id: Optional[int] = None,
) -> int:
    """
    Получение количества платежей
    """
    query = db.query(Payment)
    
    if client_id:
        query = query.filter(Payment.client_id == client_id)
    if registered_by_id:
        query = query.filter(Payment.registered_by_id == registered_by_id)
        
    return query.count()


def get_active_payments(
    db: Session,
    *,
    client_id: Optional[int] = None,
    registered_by_id: Optional[int] = None,
) -> List[Payment]:
    """
    Получение активных (неотменённых) платежей
    """
    query = db.query(Payment).filter(Payment.cancelled_at.is_(None))
    
    if client_id:
        query = query.filter(Payment.client_id == client_id)
    if registered_by_id:
        query = query.filter(Payment.registered_by_id == registered_by_id)
        
    return query.order_by(desc(Payment.payment_date)).all()


def get_cancelled_payments(
    db: Session,
    *,
    client_id: Optional[int] = None,
    registered_by_id: Optional[int] = None,
) -> List[Payment]:
    """
    Получение отменённых платежей
    """
    query = db.query(Payment).filter(Payment.cancelled_at.isnot(None))
    
    if client_id:
        query = query.filter(Payment.client_id == client_id)
    if registered_by_id:
        query = query.filter(Payment.registered_by_id == registered_by_id)
        
    return query.order_by(desc(Payment.cancelled_at)).all()


def delete_payment(db: Session, payment_id: int) -> bool:
    """
    Удаление платежа (только для отменённых)
    """
    payment = get_payment(db, payment_id)
    if not payment or not payment.cancelled_at:
        return False

    db.delete(payment)
    # НЕ делаем commit здесь - это делает сервис
    return True
