from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.models import InvoiceStatus
from app.schemas.invoice import (
    SubscriptionInvoiceCreate,
    TrainingInvoiceCreate,
    InvoiceResponse,
    InvoiceList
)
from app.services.invoice import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение информации об инвойсе.
    Доступно всем авторизованным пользователям.
    """
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/student/{student_id}", response_model=InvoiceList)
def get_student_invoices(
    student_id: int,
    status: Optional[InvoiceStatus] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка инвойсов студента.
    Доступно всем авторизованным пользователям.
    """
    service = InvoiceService(db)
    invoices = service.get_student_invoices(
        student_id=student_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return {"items": invoices, "total": len(invoices)}


@router.get("/client/{client_id}", response_model=InvoiceList)
def get_client_invoices(
    client_id: int,
    status: Optional[InvoiceStatus] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка инвойсов клиента.
    Доступно всем авторизованным пользователям.
    """
    service = InvoiceService(db)
    invoices = service.get_client_invoices(
        client_id=client_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return {"items": invoices, "total": len(invoices)}


@router.post("/subscription", response_model=InvoiceResponse)
def create_subscription_invoice(
    invoice_data: SubscriptionInvoiceCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Создание инвойса для абонемента.
    Доступно всем авторизованным пользователям.
    """
    service = InvoiceService(db)
    return service.create_subscription_invoice(
        client_id=invoice_data.client_id,
        student_id=invoice_data.student_id,
        subscription_id=invoice_data.subscription_id,
        amount=invoice_data.amount,
        description=invoice_data.description,
        is_auto_renewal=invoice_data.is_auto_renewal
    )


@router.post("/training", response_model=InvoiceResponse)
def create_training_invoice(
    invoice_data: TrainingInvoiceCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Создание инвойса для разовой тренировки.
    Доступно всем авторизованным пользователям.
    """
    service = InvoiceService(db)
    return service.create_training_invoice(
        client_id=invoice_data.client_id,
        student_id=invoice_data.student_id,
        training_id=invoice_data.training_id,
        amount=invoice_data.amount,
        description=invoice_data.description
    )


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Отмена инвойса.
    Только для админов.
    """
    service = InvoiceService(db)
    return service.cancel_invoice(
        invoice_id=invoice_id,
        cancelled_by_id=current_user["id"]
    ) 