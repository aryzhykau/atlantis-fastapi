from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.models import InvoiceStatus, InvoiceType
from app.schemas.invoice import (
    SubscriptionInvoiceCreate,
    TrainingInvoiceCreate,
    InvoiceResponse,
    InvoiceList
)
from app.services.financial import FinancialService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/", response_model=InvoiceList)
def get_invoices(
    client_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status: Optional[InvoiceStatus] = None,
    invoice_type: Optional[InvoiceType] = None,

    skip: int = 0,
    limit: int = 100,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получение списка инвойсов с фильтрами.
    Доступно всем авторизованным пользователям.
    """
    service = FinancialService(db)
    invoices = service.get_invoices(
        client_id=client_id,
        student_id=student_id,
        status=status,
        invoice_type=invoice_type,
        skip=skip,
        limit=limit
    )
    total_invoices = service.get_invoice_count(
        client_id=client_id,
        student_id=student_id,
        status=status,
    )
    return {"items": invoices, "total": total_invoices}


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
    service = FinancialService(db)
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
    service = FinancialService(db)
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
    service = FinancialService(db)
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
    service = FinancialService(db)
    try:
        return service.create_subscription_invoice(
            client_id=invoice_data.client_id,
            student_id=invoice_data.student_id,
            subscription_id=invoice_data.subscription_id,
            amount=invoice_data.amount,
            description=invoice_data.description,
            is_auto_renewal=invoice_data.is_auto_renewal
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    service = FinancialService(db)
    try:
        return service.create_training_invoice(
            client_id=invoice_data.client_id,
            student_id=invoice_data.student_id,
            training_id=invoice_data.training_id,
            amount=invoice_data.amount,
            description=invoice_data.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    service = FinancialService(db)
    try:
        return service.cancel_invoice(
            invoice_id=invoice_id,
            cancelled_by_id=current_user["id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) 