from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
import logging

from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.payment_history import PaymentHistory, OperationType
from app.utils.financial_processor import (
    create_and_pay_invoice,
    cancel_invoice,
    register_payment_with_invoice_processing
)
from app.crud import invoice as invoice_crud
from app.crud import user as user_crud

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Сервис для работы с инвойсами.
    Использует FinancialProcessor для операций и делает коммиты в базу.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_subscription_invoice(
        self,
        client_id: int,
        student_id: int,
        subscription_id: int,
        amount: float,
        description: str = None
    ) -> Invoice:
        """
        Создание инвойса за абонемент
        """
        try:
            invoice = create_and_pay_invoice(
                self.db,
                client_id=client_id,
                student_id=student_id,
                subscription_id=subscription_id,
                amount=amount,
                invoice_type=InvoiceType.SUBSCRIPTION,
                description=description or f"Абонемент #{subscription_id}"
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Subscription invoice created: {invoice.id} for client {client_id}")
            return invoice
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating subscription invoice: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def create_training_invoice(
        self,
        client_id: int,
        student_id: int,
        training_id: int,
        amount: float,
        description: str = None
    ) -> Invoice:
        """
        Создание инвойса за тренировку
        """
        try:
            invoice = create_and_pay_invoice(
                self.db,
                client_id=client_id,
                student_id=student_id,
                training_id=training_id,
                amount=amount,
                invoice_type=InvoiceType.TRAINING,
                description=description or f"Тренировка #{training_id}"
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Training invoice created: {invoice.id} for client {client_id}")
            return invoice
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating training invoice: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def cancel_invoice(
        self,
        invoice_id: int,
        cancelled_by_id: int,
        cancellation_reason: str = None
    ) -> Invoice:
        """
        Отмена инвойса с возвратом средств (если был оплачен)
        """
        try:
            cancelled_invoice = cancel_invoice(
                self.db,
                invoice_id=invoice_id,
                cancelled_by_id=cancelled_by_id
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Invoice cancelled: {invoice_id} by user {cancelled_by_id}")
            return cancelled_invoice
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error cancelling invoice: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def pay_invoice(
        self,
        invoice_id: int,
        payment_amount: float,
        registered_by_id: int,
        description: str = None
    ) -> Invoice:
        """
        Оплата инвойса с баланса клиента
        """
        try:
            # Получаем инвойс
            invoice = invoice_crud.get_invoice(self.db, invoice_id)
            if not invoice:
                raise ValueError("Invoice not found")
            
            if invoice.status == InvoiceStatus.PAID:
                raise ValueError("Invoice already paid")
            
            # Регистрируем платеж и обрабатываем инвойс
            payment = register_payment_with_invoice_processing(
                self.db,
                client_id=invoice.client_id,
                amount=payment_amount,
                description=description or f"Оплата инвойса #{invoice_id}",
                registered_by_id=registered_by_id
            )
            
            # Коммитим транзакцию
            self.db.commit()
            
            logger.info(f"Invoice paid: {invoice_id} with payment {payment.id}")
            return invoice
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def get_invoice(self, invoice_id: int) -> Invoice:
        """
        Получение инвойса по ID
        """
        invoice = invoice_crud.get_invoice(self.db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    
    def get_client_invoices(
        self,
        client_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Invoice]:
        """
        Получение инвойсов клиента
        """
        return invoice_crud.get_client_invoices(
            self.db,
            client_id=client_id,
            skip=skip,
            limit=limit
        )
    
    def get_student_invoices(
        self,
        student_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Invoice]:
        """
        Получение инвойсов студента
        """
        return invoice_crud.get_student_invoices(
            self.db,
            student_id=student_id,
            skip=skip,
            limit=limit
        ) 