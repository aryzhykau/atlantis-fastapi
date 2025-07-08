from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    User,
    UserRole,
    Payment,
    Student,
    StudentSubscription,
    RealTraining
)


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def validate_admin(self, user_id: int) -> None:
        """Проверка, что пользователь является админом"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can manage invoices"
            )

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Получение инвойса по ID"""
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_student_invoices(
        self,
        student_id: int,
        status: Optional[InvoiceStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Получение списка инвойсов студента"""
        query = self.db.query(Invoice).filter(Invoice.student_id == student_id)
        
        if status:
            query = query.filter(Invoice.status == status)
            
        return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()

    def create_subscription_invoice(
        self,
        client_id: int,
        subscription_id: int,
        amount: float,
        description: str,
        student_id: Optional[int] = None,
        is_auto_renewal: bool = False
    ) -> Invoice:
        """Создание инвойса для абонемента"""
        # Проверяем существование клиента
        client = self.db.query(User).filter(User.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        invoice_status = InvoiceStatus.UNPAID
        client_balance = client.balance
        if client_balance >= amount:
            client.balance -= amount
            self.db.refresh(client)
            invoice_status = InvoiceStatus.PAID
            
       

        # Проверяем существование студента, если указан
        if student_id:
            student = self.db.query(Student).filter(
                and_(
                    Student.id == student_id,
                    Student.client_id == client_id
                )
            ).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student not found or doesn't belong to this client")

        # Создаем инвойс
        invoice = Invoice(
            client_id=client_id,
            student_id=student_id,
            subscription_id=subscription_id,
            type=InvoiceType.SUBSCRIPTION,
            amount=amount,
            description=description,
            status=invoice_status,
            is_auto_renewal=is_auto_renewal
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def create_training_invoice(
        self,
        client_id: int,
        training_id: int,
        amount: float,
        description: str,
        student_id: Optional[int] = None
    ) -> Invoice:
        """
        Создание инвойса для разовой тренировки
        
        Args:
            client_id: ID клиента (плательщика)
            training_id: ID тренировки
            amount: Стоимость тренировки
            description: Описание
            created_by_id: Кто создал инвойс
            student_id: ID студента (опционально)
        """
        # Проверяем существование клиента
        client = self.db.query(User).filter(User.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Проверяем существование тренировки
        training = self.db.query(RealTraining).filter(RealTraining.id == training_id).first()
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")

        # Проверяем существование студента, если указан
        if student_id:
            student = self.db.query(Student).filter(
                and_(
                    Student.id == student_id,
                    Student.client_id == client_id
                )
            ).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student not found or doesn't belong to this client")

        # Создаем инвойс
        invoice = Invoice(
            client_id=client_id,
            student_id=student_id,
            training_id=training_id,
            type=InvoiceType.TRAINING,
            amount=amount,
            description=description,
            status=InvoiceStatus.UNPAID,
            is_auto_renewal=False
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def cancel_invoice(
        self,
        invoice_id: int,
        cancelled_by_id: int
    ) -> Invoice:
        """Отмена инвойса"""
        # Проверяем права
        self.validate_admin(cancelled_by_id)

        # Получаем инвойс
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Проверяем, что инвойс можно отменить
        if invoice.status == InvoiceStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Invoice is already cancelled")

        # Отменяем инвойс
        invoice.status = InvoiceStatus.CANCELLED
        invoice.cancelled_at = datetime.utcnow()
        invoice.cancelled_by_id = cancelled_by_id

        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def process_payment(
        self,
        payment: Payment,
        student_id: int
    ) -> List[Invoice]:
        """Обработка платежа и погашение инвойсов"""
        # Получаем неоплаченные инвойсы студента
        unpaid_invoices = (
            self.db.query(Invoice)
            .filter(
                and_(
                    Invoice.student_id == student_id,
                    Invoice.status == InvoiceStatus.UNPAID
                )
            )
            .order_by(Invoice.created_at)  # От старых к новым
            .all()
        )

        paid_invoices = []
        remaining_amount = payment.amount

        # Погашаем инвойсы
        for invoice in unpaid_invoices:
            if remaining_amount >= invoice.amount:
                # Оплачиваем инвойс
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = datetime.utcnow()
                invoice.payment_id = payment.id
                remaining_amount -= invoice.amount
                paid_invoices.append(invoice)
            else:
                break

        self.db.commit()
        return paid_invoices

    def revert_payment(
        self,
        invoice_id: int,
        cancelled_by_id: int
    ) -> Invoice:
        """
        Отмена платежа и возврат инвойса в неоплаченное состояние
        
        Args:
            invoice_id: ID инвойса
            cancelled_by_id: ID пользователя, отменившего платеж
            
        Returns:
            Invoice: Инвойс после отмены платежа
        """
        # Получаем инвойс
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        # Проверяем, что инвойс оплачен
        if invoice.status != InvoiceStatus.PAID:
            raise HTTPException(status_code=400, detail="Invoice is not paid")
            
        # Отменяем платеж
        invoice.status = InvoiceStatus.UNPAID
        invoice.paid_at = None
        invoice.payment_id = None
        
        self.db.commit()
        self.db.refresh(invoice)
        
        return invoice

    def create_auto_renewal_invoice(
        self,
        student_subscription: StudentSubscription
    ) -> Invoice:
        """Создание инвойса для автопродления"""
        # Получаем информацию об абонементе
        subscription = student_subscription.subscription

        # Создаем инвойс
        return self.create_subscription_invoice(
            client_id=student_subscription.student.client_id,
            subscription_id=subscription.id,
            amount=subscription.price,
            description=f"Auto-renewal: {subscription.name}",
            student_id=student_subscription.student_id,
            is_auto_renewal=True
        )

    def get_client_invoices(
        self,
        client_id: int,
        status: Optional[InvoiceStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Получение списка инвойсов клиента"""
        query = self.db.query(Invoice).filter(Invoice.client_id == client_id)
        
        if status:
            query = query.filter(Invoice.status == status)
            
        return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()

    def auto_pay_invoices(
        self,
        client_id: int,
        available_amount: float
    ) -> List[Invoice]:
        """
        Автоматическое погашение инвойсов при наличии средств на балансе
        
        Args:
            client_id: ID клиента
            available_amount: Доступная сумма для погашения
            
        Returns:
            List[Invoice]: Список оплаченных инвойсов
        """
        # Получаем клиента для проверки баланса
        client = self.db.query(User).filter(User.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
            
        # Проверяем баланс
        if client.balance < available_amount:
            raise HTTPException(
                status_code=400,
                detail="Insufficient funds"
            )
            
        # Получаем все неоплаченные инвойсы клиента
        unpaid_invoices = (
            self.db.query(Invoice)
            .filter(
                and_(
                    Invoice.client_id == client_id,
                    Invoice.status == InvoiceStatus.UNPAID
                )
            )
            .order_by(Invoice.created_at)
            .all()
        )
        
        paid_invoices = []
        remaining_amount = available_amount
        
        for invoice in unpaid_invoices:
            if remaining_amount >= invoice.amount:
                # Создаем платеж
                payment = Payment(
                    client_id=client_id,
                    amount=invoice.amount,
                    description=f"Автоматическая оплата инвойса #{invoice.id}",
                    registered_by_id=client_id  # Используем registered_by_id вместо created_by_id
                )
                self.db.add(payment)
                self.db.flush()
                
                # Обновляем инвойс
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = datetime.utcnow()
                invoice.payment_id = payment.id
                
                # Обновляем баланс клиента
                client.balance -= invoice.amount
                remaining_amount -= invoice.amount
                
                paid_invoices.append(invoice)
                
                if remaining_amount <= 0:
                    break
                    
        if paid_invoices:
            self.db.commit()
            
        return paid_invoices 