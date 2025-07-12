"""
FinancialProcessor - централизованный модуль для координации финансовых операций

Этот модуль содержит функции для:
- Создания и оплаты инвойсов
- Регистрации и отмены платежей
- Автоматической оплаты инвойсов при создании платежа
- Отмены платежей с возвратом средств

Все операции атомарны и используют CRUD операции.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crud import invoice as invoice_crud
from app.crud import payment as payment_crud
from app.crud import user as user_crud
from app.models import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentHistory,
    User,
    UserRole
)
from app.models.payment_history import OperationType
from app.schemas.invoice import InvoiceCreate
from app.schemas.payment import PaymentCreate

logger = logging.getLogger(__name__)


def validate_admin_or_trainer(db: Session, user_id: int) -> None:
    """Проверка, что пользователь является админом или тренером"""
    user = user_crud.get_user_by_id(db, user_id)
    if not user or user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise ValueError("Only admins and trainers can manage payments")


def validate_admin(db: Session, user_id: int) -> None:
    """Проверка, что пользователь является админом"""
    user = user_crud.get_user_by_id(db, user_id)
    if not user or user.role != UserRole.ADMIN:
        raise ValueError("Only admins can perform this operation")


def create_and_pay_invoice(
    db: Session,
    invoice_data: InvoiceCreate,
    auto_pay: bool = True
) -> Invoice:
    """
    Создание инвойса с возможностью автоматической оплаты
    
    Args:
        db: Сессия базы данных
        invoice_data: Данные для создания инвойса
        auto_pay: Автоматически оплатить инвойс, если есть средства
        
    Returns:
        Invoice: Созданный инвойс
    """
    if auto_pay:
        # Проверяем баланс клиента ПЕРЕД созданием инвойса
        client = user_crud.get_user_by_id(db, invoice_data.client_id)
        if client and client.balance >= invoice_data.amount:
            # Если баланса хватает, создаем инвойс как оплаченный
            invoice_data.status = InvoiceStatus.PAID
            
            # Создаем инвойс
            invoice = invoice_crud.create_invoice(db, invoice_data)
            
            # Обновляем баланс клиента
            new_balance = client.balance - invoice_data.amount
            user_crud.update_user_balance(db, client.id, new_balance)
            
            # Создаем запись в истории
            history = PaymentHistory(
                client_id=invoice.client_id,
                payment_id=None,  # Нет конкретного платежа
                invoice_id=invoice.id,
                operation_type=OperationType.INVOICE_PAYMENT,
                amount=-invoice.amount,
                balance_before=client.balance + invoice.amount,
                balance_after=client.balance,
                created_by_id=invoice.client_id,
                description=f"Автоматическая оплата инвойса #{invoice.id}"
            )
            db.add(history)
        else:
            # Если баланса не хватает, создаем как неоплаченный
            invoice_data.status = InvoiceStatus.UNPAID
            invoice = invoice_crud.create_invoice(db, invoice_data)
    else:
        # Создаем инвойс без попытки оплаты
        invoice = invoice_crud.create_invoice(db, invoice_data)
    
    return invoice


def register_payment_with_invoice_processing(
    db: Session,
    client_id: int,
    amount: float,
    registered_by_id: int,
    description: Optional[str] = None
) -> Tuple[Payment, List[Invoice]]:
    """
    Регистрация платежа с автоматической обработкой инвойсов
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        amount: Сумма платежа
        registered_by_id: ID пользователя, зарегистрировавшего платеж
        description: Описание платежа
        
    Returns:
        Tuple[Payment, List[Invoice]]: Созданный платеж и список оплаченных инвойсов
    """
    # Проверяем права доступа
    validate_admin_or_trainer(db, registered_by_id)
    
    # Валидация
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    
    if description and len(description) > 500:
        raise ValueError("Payment description is too long (max 500 characters)")
    
    # Получаем клиента
    client = user_crud.get_user_by_id(db, client_id)
    if not client:
        raise ValueError("Client not found")
    
    current_balance = client.balance or 0.0
    
    # Создаем платеж
    payment_data = PaymentCreate(
        client_id=client_id,
        amount=amount,
        description=description,
        registered_by_id=registered_by_id
    )
    payment = payment_crud.create_payment(db, payment_data)
    
    # Обновляем баланс клиента
    new_balance = current_balance + amount
    user_crud.update_user_balance(db, client_id, new_balance)
    
    # Создаем запись в истории платежа
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
    db.add(history)
    
    # Пытаемся оплатить инвойсы из обновленного баланса
    paid_invoices = process_invoice_payments(db, client_id, new_balance, registered_by_id)
    
    return payment, paid_invoices


def process_invoice_payments(
    db: Session,
    client_id: int,
    available_balance: float,
    processed_by_id: int
) -> List[Invoice]:
    """
    Обработка оплаты инвойсов из доступного баланса
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        available_balance: Доступный баланс
        processed_by_id: ID пользователя, обрабатывающего платежи
        
    Returns:
        List[Invoice]: Список оплаченных инвойсов
    """
    # Получаем неоплаченные инвойсы, отсортированные по дате создания
    unpaid_invoices = invoice_crud.get_unpaid_invoices(db, client_id=client_id)
    
    paid_invoices = []
    remaining_balance = available_balance
    
    for invoice in unpaid_invoices:
        if remaining_balance >= invoice.amount:
            # Отмечаем инвойс как оплаченный
            invoice_crud.mark_invoice_as_paid(db, invoice.id)
            
            # Обновляем баланс клиента
            remaining_balance -= invoice.amount
            user_crud.update_user_balance(db, client_id, remaining_balance)
            
            # Создаем запись в истории об оплате инвойса
            invoice_payment_history = PaymentHistory(
                client_id=client_id,
                payment_id=None,  # Не привязываем к конкретному платежу
                invoice_id=invoice.id,
                operation_type=OperationType.INVOICE_PAYMENT,
                amount=-invoice.amount,
                balance_before=remaining_balance + invoice.amount,
                balance_after=remaining_balance,
                created_by_id=processed_by_id,
                description=f"Оплата инвойса #{invoice.id}"
            )
            db.add(invoice_payment_history)
            
            paid_invoices.append(invoice)
        else:
            # Если баланса не хватает, прекращаем обработку
            break
    
    return paid_invoices


def cancel_payment_with_refunds(
    db: Session,
    payment_id: int,
    cancelled_by_id: int,
    cancellation_reason: Optional[str] = None
) -> Tuple[Payment, List[Invoice]]:
    """
    Отмена платежа с возвратом средств и отменой инвойсов
    
    Args:
        db: Сессия базы данных
        payment_id: ID платежа
        cancelled_by_id: ID пользователя, отменившего платеж
        cancellation_reason: Причина отмены
        
    Returns:
        Tuple[Payment, List[Invoice]]: Отмененный платеж и список отмененных инвойсов
    """
    # Проверяем права
    validate_admin(db, cancelled_by_id)
    
    # Получаем платеж
    payment = payment_crud.get_payment(db, payment_id)
    if not payment:
        raise ValueError("Payment not found")
    
    if payment.cancelled_at:
        raise ValueError("Payment already cancelled")
    
    # Получаем клиента и его текущий баланс
    client = user_crud.get_user_by_id(db, payment.client_id)
    current_balance = client.balance or 0.0
    
    cancelled_invoices = []
    
    # Сравниваем баланс с суммой платежа
    if current_balance >= payment.amount:
        # Если баланс достаточный, просто уменьшаем его
        new_balance = current_balance - payment.amount
        user_crud.update_user_balance(db, client.id, new_balance)
        
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
        db.add(history)
    else:
        # Если баланса недостаточно, зануляем баланс и отменяем инвойсы
        remaining_amount = payment.amount - current_balance
        
        # Зануляем баланс
        user_crud.update_user_balance(db, client.id, 0.0)
        
        # Создаем запись в истории о списании всего баланса
        history = PaymentHistory(
            payment_id=payment.id,
            client_id=payment.client_id,
            operation_type=OperationType.CANCELLATION,
            amount=-current_balance,
            balance_before=current_balance,
            balance_after=0.0,
            created_by_id=cancelled_by_id,
            description=f"Частичная отмена платежа ({cancellation_reason})"
        )
        db.add(history)
        
        # Отменяем инвойсы, начиная с новых
        cancelled_invoices = cancel_invoices_for_refund(
            db, payment.client_id, remaining_amount, cancelled_by_id
        )
    
    # Отмечаем платеж как отмененный
    payment.cancelled_at = datetime.now(timezone.utc)
    payment.cancelled_by_id = cancelled_by_id
    db.add(payment)
    
    return payment, cancelled_invoices


def cancel_invoices_for_refund(
    db: Session,
    client_id: int,
    remaining_amount: float,
    cancelled_by_id: int
) -> List[Invoice]:
    """
    Отмена инвойсов для возврата средств
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        remaining_amount: Оставшаяся сумма для возврата
        cancelled_by_id: ID пользователя, отменившего платеж
        
    Returns:
        List[Invoice]: Список отмененных инвойсов
    """
    # Получаем все оплаченные инвойсы клиента, начиная с новых
    paid_invoices = invoice_crud.get_paid_invoices(db, client_id=client_id)
    
    cancelled_invoices = []
    
    for invoice in paid_invoices:
        if remaining_amount <= 0:
            break
        
        invoice_amount = invoice.amount
        
        if remaining_amount >= invoice_amount:
            # Полная отмена инвойса через CRUD
            cancelled_invoice = invoice_crud.mark_invoice_as_unpaid(db, invoice.id)
            if cancelled_invoice:
                remaining_amount -= invoice_amount
                
                # Создаем запись в истории об отмене оплаты инвойса
                invoice_cancel_history = PaymentHistory(
                    client_id=client_id,
                    payment_id=None,
                    invoice_id=invoice.id,
                    operation_type=OperationType.CANCELLATION,
                    amount=0,
                    balance_before=0,
                    balance_after=0,
                    created_by_id=cancelled_by_id,
                    description=f"Отмена оплаты инвойса #{invoice.id}"
                )
                db.add(invoice_cancel_history)
                
                cancelled_invoices.append(cancelled_invoice)
        else:
            # Частичная отмена инвойса через CRUD
            cancelled_invoice = invoice_crud.mark_invoice_as_unpaid(db, invoice.id)
            if cancelled_invoice:
                # Добавляем остаток разницы на баланс
                partial_refund = invoice_amount - remaining_amount
                user_crud.update_user_balance(db, client_id, partial_refund)
                
                # Создаем запись в истории
                invoice_partial_history = PaymentHistory(
                    client_id=client_id,
                    payment_id=None,
                    invoice_id=invoice.id,
                    operation_type=OperationType.CANCELLATION,
                    amount=partial_refund,
                    balance_before=0,
                    balance_after=partial_refund,
                    created_by_id=cancelled_by_id,
                    description=f"Отмена оплаты инвойса #{invoice.id} с частичным возвратом"
                )
                db.add(invoice_partial_history)
                
                cancelled_invoices.append(cancelled_invoice)
                break
    
    return cancelled_invoices


def cancel_invoice(
    db: Session,
    invoice_id: int,
    cancelled_by_id: int
) -> Invoice:
    """
    Отмена инвойса
    
    Args:
        db: Сессия базы данных
        invoice_id: ID инвойса
        cancelled_by_id: ID пользователя, отменившего инвойс
        
    Returns:
        Invoice: Отмененный инвойс
    """
    # Проверяем права
    validate_admin(db, cancelled_by_id)
    
    # Получаем инвойс
    invoice = invoice_crud.get_invoice(db, invoice_id)
    if not invoice:
        raise ValueError("Invoice not found")
    
    # Если инвойс был оплачен, возвращаем средства на баланс клиента
    if invoice.status == InvoiceStatus.PAID:
        client = user_crud.get_user_by_id(db, invoice.client_id)
        if client:
            # Возвращаем средства на баланс
            new_balance = client.balance + invoice.amount
            user_crud.update_user_balance(db, client.id, new_balance)
            
            # Создаем запись в истории
            history = PaymentHistory(
                client_id=invoice.client_id,
                payment_id=None,
                invoice_id=invoice.id,
                operation_type=OperationType.CANCELLATION,
                amount=invoice.amount,  # Положительная сумма - возврат средств
                balance_before=client.balance,
                balance_after=new_balance,
                created_by_id=cancelled_by_id,
                description=f"Отмена инвойса #{invoice.id} - возврат средств"
            )
            db.add(history)
    
    # Отменяем инвойс через CRUD
    cancelled_invoice = invoice_crud.cancel_invoice(db, invoice_id)
    if not cancelled_invoice:
        raise ValueError("Failed to cancel invoice")
    
    # Устанавливаем дополнительные поля
    cancelled_invoice.cancelled_by_id = cancelled_by_id
    
    return cancelled_invoice 