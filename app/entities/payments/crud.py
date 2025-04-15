import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.entities.invoices.models import Invoice
from app.entities.payments.models import Payment
from app.entities.payments.schemas import PaymentCreate
from app.entities.users.models import User

logger = logging.getLogger(__name__)
#
#
def create_payment(db: Session, payment: PaymentCreate):
    try:
        new_payment = payment.model_dump()
        client = db.query(User).filter(User.id == payment.user_id).first()
        if not client:
            raise ValueError(f"User with id {payment.user_id} not found")
        db_payment = Payment(**new_payment)
        db.add(db_payment)
        client.balance += db_payment.amount
        client_invoices = db.query(Invoice).filter(Invoice.user_id == client.id, Invoice.paid_at == None).order_by(Invoice.created_at.desc()).all()

        for invoice in client_invoices:
            if invoice.amount <= 0:
                logger.error(f"Invalid invoice amount: {invoice.amount} for invoice {invoice.id}")
                continue

            if invoice.amount > client.balance:
                break
            client.balance -= invoice.amount
            invoice.paid_at = datetime.now()

        db.commit()
        db.refresh(db_payment)
        return db_payment
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating payment: {e}")
        raise e


def get_payments(db: Session, user_id: Optional[int]= None):
    payments = db.query(Payment)
    filters = []
    if user_id:
        filters.append(Payment.user_id == user_id)
    if filters:
        payments = payments.filter(and_(*filters))
    payments = payments.all()
    return payments
