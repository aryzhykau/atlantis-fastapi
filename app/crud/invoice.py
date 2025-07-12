from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models import Invoice, InvoiceStatus, InvoiceType
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ С ИНВОЙСАМИ
# =============================================================================

def get_invoice(db: Session, invoice_id: int) -> Optional[Invoice]:
    """
    Получение инвойса по ID
    """
    return db.query(Invoice).filter(Invoice.id == invoice_id).first()


def get_invoices(
    db: Session,
    *,
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status: Optional[InvoiceStatus] = None,
    invoice_type: Optional[InvoiceType] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Invoice]:
    """
    Получение списка инвойсов с фильтрами
    """
    query = db.query(Invoice)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)
    if status:
        query = query.filter(Invoice.status == status)
    if invoice_type:
        query = query.filter(Invoice.type == invoice_type)
        
    return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()


def get_student_invoices(
    db: Session,
    student_id: int,
    *,
    status: Optional[InvoiceStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Invoice]:
    """
    Получение списка инвойсов студента
    """
    query = db.query(Invoice).filter(Invoice.student_id == student_id)
    
    if status:
        query = query.filter(Invoice.status == status)
        
    return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()


def get_client_invoices(
    db: Session,
    client_id: int,
    *,
    status: Optional[InvoiceStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Invoice]:
    """
    Получение списка инвойсов клиента
    """
    query = db.query(Invoice).filter(Invoice.client_id == client_id)
    
    if status:
        query = query.filter(Invoice.status == status)
        
    return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()


def get_training_invoice(
    db: Session,
    training_id: int,
    student_id: int,
) -> Optional[Invoice]:
    """
    Получение инвойса за конкретную тренировку студента
    """
    return db.query(Invoice).filter(
        and_(
            Invoice.training_id == training_id,
            Invoice.student_id == student_id,
            Invoice.status != InvoiceStatus.CANCELLED
        )
    ).first()


def get_subscription_invoice(
    db: Session,
    subscription_id: int,
    student_id: int,
) -> Optional[Invoice]:
    """
    Получение инвойса за абонемент студента
    """
    return db.query(Invoice).filter(
        and_(
            Invoice.subscription_id == subscription_id,
            Invoice.student_id == student_id,
            Invoice.status != InvoiceStatus.CANCELLED
        )
    ).first()


def create_invoice(db: Session, invoice_data: InvoiceCreate) -> Invoice:
    """
    Создание нового инвойса
    """
    invoice = Invoice(
        client_id=invoice_data.client_id,
        student_id=invoice_data.student_id,
        training_id=invoice_data.training_id,
        subscription_id=invoice_data.subscription_id,
        type=invoice_data.type,
        amount=invoice_data.amount,
        description=invoice_data.description,
        status=invoice_data.status,
        is_auto_renewal=invoice_data.is_auto_renewal,
    )
    db.add(invoice)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(invoice)
    return invoice


def update_invoice(
    db: Session,
    invoice_id: int,
    update_data: InvoiceUpdate,
) -> Optional[Invoice]:
    """
    Обновление инвойса
    """
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(invoice, field, value)

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(invoice)
    return invoice


def cancel_invoice(db: Session, invoice_id: int) -> Optional[Invoice]:
    """
    Отмена инвойса
    """
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        return None

    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancelled_at = datetime.now(timezone.utc)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(invoice)
    return invoice


def mark_invoice_as_paid(
    db: Session, 
    invoice_id: int, 
    paid_at: Optional[datetime] = None
) -> Optional[Invoice]:
    """
    Отметка инвойса как оплаченного
    """
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        return None

    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = paid_at or datetime.now(timezone.utc)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(invoice)
    return invoice


def mark_invoice_as_unpaid(
    db: Session, 
    invoice_id: int
) -> Optional[Invoice]:
    """
    Возврат инвойса в неоплаченное состояние
    """
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        return None

    invoice.status = InvoiceStatus.UNPAID
    invoice.paid_at = None
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(invoice)
    return invoice


def get_unpaid_invoices(
    db: Session,
    *,
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
) -> List[Invoice]:
    """
    Получение неоплаченных инвойсов
    """
    query = db.query(Invoice).filter(Invoice.status == InvoiceStatus.UNPAID)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)
        
    return query.order_by(Invoice.created_at).all()


def get_paid_invoices(
    db: Session,
    *,
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Invoice]:
    """
    Получение оплаченных инвойсов
    """
    query = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)
    if start_date:
        query = query.filter(Invoice.paid_at >= start_date)
    if end_date:
        query = query.filter(Invoice.paid_at <= end_date)
        
    return query.order_by(desc(Invoice.paid_at)).all()


def get_cancelled_invoices(
    db: Session,
    *,
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
) -> List[Invoice]:
    """
    Получение отменённых инвойсов
    """
    query = db.query(Invoice).filter(Invoice.status == InvoiceStatus.CANCELLED)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)
        
    return query.order_by(desc(Invoice.cancelled_at)).all()


def delete_invoice(db: Session, invoice_id: int) -> bool:
    """
    Удаление инвойса (только для отменённых)
    """
    invoice = get_invoice(db, invoice_id)
    if not invoice or invoice.status != InvoiceStatus.CANCELLED:
        return False

    db.delete(invoice)
    # НЕ делаем commit здесь - это делает сервис
    return True


def get_invoice_count(
    db: Session,
    *,
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status: Optional[InvoiceStatus] = None,
) -> int:
    """
    Получение количества инвойсов
    """
    query = db.query(Invoice)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if student_id:
        query = query.filter(Invoice.student_id == student_id)
    if status:
        query = query.filter(Invoice.status == status)
        
    return query.count() 