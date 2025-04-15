import datetime
import logging
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.entities.invoices.models import Invoice
from app.entities.invoices.schemas import InvoiceCreate
from app.entities.users.models import User

logger = logging.getLogger(__name__)

def create_invoice(db: Session, invoice: InvoiceCreate):
    try:
        new_invoice = invoice.model_dump()
        if new_invoice["created_at"] is None:
            new_invoice["created_at"] = datetime.datetime.now()
        db_client = db.query(User).filter(User.id == new_invoice["user_id"]).first()
        db_invoice = Invoice(**new_invoice)
        if db_client.balance >= new_invoice.amount:
            setattr(db_client, "balance", db_client.balance - new_invoice.amount)
            db_invoice.paid_at = datetime.now()

        db.add(db_invoice)

        db.commit()
        db.refresh(db_invoice)
        return db_invoice
    except Exception as e:
        db.rollback()
        raise e


def get_all_invoices(db: Session, user_id: Optional[int] = None, only_unpaid: bool = False):
    try:
        invoices = db.query(Invoice)
        logger.debug(f"{user_id}, {only_unpaid}")
        filters = []
        if user_id:
            filters.append(Invoice.user_id == user_id)
        if only_unpaid is not False:  # Фильтруем по оплате, если передан параметр
            filters.append(Invoice.paid_at.is_(None))  # Неоплаченные счета
        if filters:
            invoices = invoices.filter(and_(*filters))
        invoices = invoices.all()
        return invoices
    except Exception as e:
        raise e


