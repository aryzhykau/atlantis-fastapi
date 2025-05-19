from datetime import datetime
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
from app.services.invoice import InvoiceService


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)

    def validate_admin_or_trainer(self, user_id: int) -> None:
        """Проверка, что пользователь является админом или тренером"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
            raise HTTPException(
                status_code=403,
                detail="Only admins and trainers can manage payments"
            )

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Получение платежа по ID"""
        payment = crud.get_payment(self.db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    def get_client_payments(
        self,
        client_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Payment]:
        """Получение списка платежей клиента"""
        return crud.get_client_payments(self.db, client_id, skip, limit)

    def register_payment(
        self,
        client_id: int,
        amount: float,
        description: str,
        registered_by_id: int
    ) -> Payment:
        """
        Регистрация нового платежа
        1. Проверяем права доступа
        2. Валидируем сумму платежа
        3. Создаем платеж
        4. Обновляем баланс клиента
        5. Создаем запись в истории
        6. Запускаем автоматическое погашение инвойсов
        """
        # Проверяем права доступа
        self.validate_admin_or_trainer(registered_by_id)

        # Валидация описания
        if not description or len(description.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Payment description cannot be empty"
            )
        if len(description) > 500:
            raise HTTPException(
                status_code=400,
                detail="Payment description is too long (max 500 characters)"
            )

        # Валидация суммы платежа
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Payment amount must be greater than zero"
            )

        try:
            # Получаем клиента и его текущий баланс
            client = self.db.query(User).filter(User.id == client_id).first()
            if not client:
                raise ValueError("Client not found")
            
            current_balance = client.balance or 0.0

            # Создаем платеж
            payment = crud.create_payment(
                self.db,
                client_id=client_id,
                amount=amount,
                description=description,
                registered_by_id=registered_by_id
            )

            # Получаем неоплаченные инвойсы, отсортированные по дате создания
            unpaid_invoices = self.db.query(Invoice).filter(
                Invoice.client_id == client_id,
                Invoice.status == InvoiceStatus.UNPAID
            ).order_by(Invoice.created_at.asc()).all()

            # Вычитаем из суммы платежа оплату инвойсов
            remaining_amount = amount
            for invoice in unpaid_invoices:
                if remaining_amount >= invoice.amount:
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = datetime.utcnow()
                    invoice.payment_id = payment.id
                    remaining_amount -= invoice.amount
                    self.db.add(invoice)
                if remaining_amount <= 0:
                    break

            # Обновляем баланс клиента на оставшуюся сумму
            new_balance = current_balance + remaining_amount
            client.balance = new_balance
            self.db.add(client)

            # Создаем запись в истории
            history = PaymentHistory(
                client_id=client_id,
                payment_id=payment.id,
                operation_type=OperationType.PAYMENT,
                amount=amount,
                balance_before=current_balance,
                balance_after=new_balance,
                created_by_id=registered_by_id,
                description=description
            )
            self.db.add(history)

            self.db.commit()
            return payment
            
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def cancel_payment(
        self,
        payment_id: int,
        cancelled_by_id: int,
        cancellation_reason: str = None
    ) -> Payment:
        """
        Отмена платежа
        1. Проверяем права доступа (только админ)
        2. Отменяем платеж
        3. Отменяем оплату связанных инвойсов
        4. Обновляем баланс клиента
        5. Создаем запись в истории
        """
        # Проверяем, что отменяет админ
        user = self.db.query(User).filter(User.id == cancelled_by_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can cancel payments"
            )

        payment = self.get_payment(payment_id)
        if payment.cancelled_at:
            raise HTTPException(
                status_code=400,
                detail="Payment already cancelled"
            )

        # Получаем текущий баланс клиента
        client = self.db.query(User).filter(User.id == payment.client_id).first()
        current_balance = client.balance or 0.0

        # Отменяем оплату связанных инвойсов
        paid_invoices = self.db.query(Invoice).filter(
            Invoice.payment_id == payment_id,
            Invoice.status == InvoiceStatus.PAID
        ).all()

        for invoice in paid_invoices:
            invoice.status = InvoiceStatus.UNPAID
            invoice.paid_at = None
            invoice.payment_id = None
            self.db.add(invoice)

        # Отменяем платеж
        payment.cancelled_at = datetime.utcnow()
        payment.cancelled_by_id = cancelled_by_id
        self.db.add(payment)

        # Обновляем баланс клиента
        new_balance = current_balance - payment.amount
        client.balance = new_balance
        self.db.add(client)

        # Создаем запись в истории
        history = PaymentHistory(
            payment_id=payment.id,
            client_id=payment.client_id,
            operation_type=OperationType.CANCELLATION,
            amount=-payment.amount,
            balance_before=current_balance,
            balance_after=new_balance,
            created_by_id=cancelled_by_id,
            description=cancellation_reason
        )
        self.db.add(history)

        self.db.commit()
        return payment

    def get_client_balance(self, client_id: int) -> float:
        """Получение текущего баланса клиента"""
        client = self.db.query(User).filter(User.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client.balance or 0.0

    def get_payment_history(
        self,
        user_id: int,
        client_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PaymentHistory]:
        """
        Получение истории платежей клиента
        Доступно только для админов и тренеров
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
            raise HTTPException(
                status_code=403,
                detail="Only admins and trainers can view payment history"
            )

        return self.db.query(PaymentHistory).filter(
            PaymentHistory.client_id == client_id
        ).order_by(desc(PaymentHistory.created_at)).offset(skip).limit(limit).all()

    def register_training_payment(
        self,
        client_id: int,
        amount: float,
        training_id: int,
        registered_by_id: int
    ) -> Payment:
        """
        Регистрация платежа через отметку присутствия на тренировке
        """
        # Проверяем, что регистрирует тренер
        user = self.db.query(User).filter(User.id == registered_by_id).first()
        if not user or user.role != UserRole.TRAINER:
            raise HTTPException(
                status_code=403,
                detail="Only trainers can register training payments"
            )

        description = f"Payment for training #{training_id}"
        return self.register_payment(
            client_id=client_id,
            amount=amount,
            description=description,
            registered_by_id=registered_by_id
        ) 