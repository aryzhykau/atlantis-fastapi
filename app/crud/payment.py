from datetime import datetime
from typing import Optional, List
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
    skip: int = 0,
    limit: int = 100
) -> List[Payment]:
    """Получение списка платежей клиента"""
    return (
        db.query(Payment)
        .filter(Payment.client_id == client_id)
        .order_by(desc(Payment.payment_date))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_payment(
    db: Session,
    client_id: int,
    amount: float,
    description: str,
    registered_by_id: int
) -> Payment:
    """
    Создание нового платежа
    """
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise ValueError("Client not found")

    payment = Payment(
        client_id=client_id,
        amount=amount,
        description=description,
        registered_by_id=registered_by_id
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def cancel_payment(
    db: Session,
    payment_id: int,
    cancelled_by_id: int
) -> Optional[Payment]:
    """Отмена платежа"""
    # Получаем платеж
    payment = get_payment(db, payment_id)
    if not payment or payment.cancelled_at:
        return None
    
    # Получаем клиента
    client = db.query(User).filter(User.id == payment.client_id).first()
    if not client:
        raise ValueError("Client not found")
    
    current_balance = client.balance or 0.0
    new_balance = current_balance - payment.amount
    
    # Отмечаем платеж как отмененный
    payment.cancelled_at = datetime.utcnow()
    payment.cancelled_by_id = cancelled_by_id
    
    # Создаем запись в истории
    payment_history = PaymentHistory(
        client_id=client.id,
        payment_id=payment.id,
        operation_type=OperationType.CANCELLATION,
        amount=-payment.amount,  # Отрицательная сумма для отмены
        balance_before=current_balance,
        balance_after=new_balance,
        created_by_id=cancelled_by_id
    )
    db.add(payment_history)
    
    # Обновляем баланс клиента
    client.balance = new_balance
    
    db.commit()
    db.refresh(payment)
    return payment 