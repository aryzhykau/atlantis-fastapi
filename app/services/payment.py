import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.crud import payment as crud
from app.models import (
    Payment,
    User,
    UserRole,
    PaymentHistory,
    Invoice,
    InvoiceStatus
)
from app.models.payment_history import OperationType
from app.utils.financial_processor import (
    register_payment_with_invoice_processing,
    cancel_payment_with_refunds,
    validate_admin_or_trainer
)

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Получение платежа по ID"""
        payment = crud.get_payment(self.db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    def get_payments(
        self,
        client_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Payment]:
        """Получение списка платежей"""
        return crud.get_payments(
            self.db,
            client_id=client_id,
            skip=skip,
            limit=limit
        )

    def register_payment(
        self,
        client_id: int,
        amount: float,
        registered_by_id: int,
        description: Optional[str] = None
    ) -> Payment:
        """
        Регистрация нового платежа с автоматической обработкой инвойсов
        """
        try:
            payment, paid_invoices = register_payment_with_invoice_processing(
                self.db,
                client_id=client_id,
                amount=amount,
                registered_by_id=registered_by_id,
                description=description
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Payment registered: {payment.id}, paid invoices: {len(paid_invoices)}")
            return payment
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error registering payment: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def cancel_payment(
        self,
        payment_id: int,
        cancelled_by_id: int,
        cancellation_reason: str = None
    ) -> Payment:
        """
        Отмена платежа с возвратом средств и отменой инвойсов
        """
        try:
            payment, cancelled_invoices = cancel_payment_with_refunds(
                self.db,
                payment_id=payment_id,
                cancelled_by_id=cancelled_by_id,
                cancellation_reason=cancellation_reason
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Payment cancelled: {payment.id}, cancelled invoices: {len(cancelled_invoices)}")
            return payment
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_payment_history(
        self,
        client_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PaymentHistory]:
        """Получение истории платежей клиента"""
        return crud.get_payment_history(
            self.db,
            client_id=client_id,
            skip=skip,
            limit=limit
        ) 