from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Invoice, Payment, InvoiceStatus, PaymentHistory
from app.crud import invoice as invoice_crud
from app.crud import payment as payment_crud


# =============================================================================
# ВАЛИДАЦИЯ ИНВОЙСОВ
# =============================================================================

def validate_invoice_exists(db: Session, invoice_id: int) -> Optional[Invoice]:
    """
    Проверка существования инвойса
    
    Returns:
        Invoice если существует, None если нет
    """
    return invoice_crud.get_invoice(db, invoice_id)


def validate_invoice_not_cancelled(invoice: Invoice) -> bool:
    """
    Проверка, что инвойс не отменён
    
    Returns:
        True если инвойс не отменён, False если отменён
    """
    return invoice.status != InvoiceStatus.CANCELLED


def validate_invoice_not_paid(invoice: Invoice) -> bool:
    """
    Проверка, что инвойс не оплачен
    
    Returns:
        True если инвойс не оплачен, False если оплачен
    """
    return invoice.status != InvoiceStatus.PAID


def validate_invoice_amount(invoice: Invoice, amount: float) -> bool:
    """
    Проверка корректности суммы инвойса
    
    Returns:
        True если сумма корректная, False если нет
    """
    return invoice.amount == amount


def validate_invoice_can_be_cancelled(invoice: Invoice) -> bool:
    """
    Проверка, можно ли отменить инвойс
    
    Returns:
        True если можно отменить, False если нет
    """
    # Можно отменить только неоплаченные инвойсы
    return invoice.status == InvoiceStatus.UNPAID


def validate_invoice_can_be_paid(invoice: Invoice) -> bool:
    """
    Проверка, можно ли оплатить инвойс
    
    Returns:
        True если можно оплатить, False если нет
    """
    # Можно оплатить только неоплаченные и неотменённые инвойсы
    return invoice.status == InvoiceStatus.UNPAID


# =============================================================================
# ВАЛИДАЦИЯ ПЛАТЕЖЕЙ
# =============================================================================

def validate_payment_exists(db: Session, payment_id: int) -> Optional[Payment]:
    """
    Проверка существования платежа
    
    Returns:
        Payment если существует, None если нет
    """
    return payment_crud.get_payment(db, payment_id)


def validate_payment_not_cancelled(payment: Payment) -> bool:
    """
    Проверка, что платеж не отменён
    
    Returns:
        True если платеж не отменён, False если отменён
    """
    return payment.cancelled_at is None


def validate_payment_amount(payment: Payment, amount: float) -> bool:
    """
    Проверка корректности суммы платежа
    
    Returns:
        True если сумма корректная, False если нет
    """
    return payment.amount == amount


def validate_payment_can_be_cancelled(payment: Payment) -> bool:
    """
    Проверка, можно ли отменить платеж
    
    Returns:
        True если можно отменить, False если нет
    """
    # Можно отменить только неотменённые платежи
    return payment.cancelled_at is None


def validate_payment_amount_positive(amount: float) -> bool:
    """
    Проверка, что сумма платежа положительная
    
    Returns:
        True если сумма положительная, False если нет
    """
    return amount > 0


def validate_payment_description(description: Optional[str]) -> bool:
    """
    Проверка корректности описания платежа
    
    Returns:
        True если описание корректное, False если нет
    """
    if description is None:
        return True  # Описание может быть пустым
    
    return len(description.strip()) > 0


# =============================================================================
# ВАЛИДАЦИЯ ФИНАНСОВЫХ ОПЕРАЦИЙ
# =============================================================================

def validate_client_balance_sufficient(
    db: Session,
    client_id: int,
    required_amount: float
) -> bool:
    """
    Проверка достаточности баланса клиента
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        required_amount: Требуемая сумма
    
    Returns:
        True если баланс достаточен, False если нет
    """
    # Получаем все активные платежи клиента
    payments = payment_crud.get_active_payments(db, client_id=client_id)
    
    # Считаем общую сумму платежей
    total_payments = sum(payment.amount for payment in payments)
    
    # Получаем все неоплаченные инвойсы клиента
    invoices = invoice_crud.get_unpaid_invoices(db, client_id=client_id)
    
    # Считаем общую сумму инвойсов
    total_invoices = sum(invoice.amount for invoice in invoices)
    
    # Вычисляем баланс
    balance = total_payments - total_invoices
    
    return balance >= required_amount


def validate_invoice_payment_match(
    invoice: Invoice,
    payment: Payment
) -> bool:
    """
    Проверка соответствия инвойса и платежа
    
    Returns:
        True если соответствуют, False если нет
    """
    # Проверяем, что клиент совпадает
    if invoice.client_id != payment.client_id:
        return False
    
    # Проверяем, что суммы совпадают
    if invoice.amount != payment.amount:
        return False
    
    return True


def validate_payment_history_operation(
    operation_type: str,
    amount: float,
    balance_before: float,
    balance_after: float
) -> bool:
    """
    Проверка корректности операции в истории платежей
    
    Returns:
        True если операция корректная, False если нет
    """
    # Проверяем, что сумма положительная
    if amount <= 0:
        return False
    
    # Проверяем корректность баланса
    expected_balance_after = balance_before + amount
    if abs(balance_after - expected_balance_after) > 0.01:  # Учитываем погрешность
        return False
    
    return True


# =============================================================================
# КОМПЛЕКСНЫЕ ВАЛИДАЦИИ
# =============================================================================

def validate_invoice_for_payment(
    db: Session,
    invoice_id: int,
    payment_amount: float
) -> tuple[bool, str]:
    """
    Комплексная валидация для оплаты инвойса
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование инвойса
    invoice = validate_invoice_exists(db, invoice_id)
    if not invoice:
        return False, "Инвойс не найден"
    
    # Проверяем, что инвойс не отменён
    if not validate_invoice_not_cancelled(invoice):
        return False, "Инвойс отменён"
    
    # Проверяем, что инвойс не оплачен
    if not validate_invoice_not_paid(invoice):
        return False, "Инвойс уже оплачен"
    
    # Проверяем соответствие суммы
    if not validate_invoice_amount(invoice, payment_amount):
        return False, "Сумма платежа не соответствует сумме инвойса"
    
    return True, ""


def validate_payment_for_cancellation(
    db: Session,
    payment_id: int
) -> tuple[bool, str]:
    """
    Комплексная валидация для отмены платежа
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем существование платежа
    payment = validate_payment_exists(db, payment_id)
    if not payment:
        return False, "Платёж не найден"
    
    # Проверяем, что платеж не отменён
    if not validate_payment_not_cancelled(payment):
        return False, "Платёж уже отменён"
    
    # Проверяем, что платеж можно отменить
    if not validate_payment_can_be_cancelled(payment):
        return False, "Платёж нельзя отменить"
    
    return True, ""


def validate_client_financial_operation(
    db: Session,
    client_id: int,
    operation_amount: float,
    operation_type: str
) -> tuple[bool, str]:
    """
    Комплексная валидация для финансовой операции клиента
    
    Args:
        db: Сессия базы данных
        client_id: ID клиента
        operation_amount: Сумма операции
        operation_type: Тип операции ('payment' или 'invoice')
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем корректность суммы
    if not validate_payment_amount_positive(operation_amount):
        return False, "Сумма операции должна быть положительной"
    
    # Для платежей дополнительных проверок нет
    if operation_type == 'payment':
        return True, ""
    
    # Для инвойсов проверяем баланс
    if operation_type == 'invoice':
        if not validate_client_balance_sufficient(db, client_id, operation_amount):
            return False, "Недостаточно средств на балансе"
    
    return True, ""


def validate_training_invoice_creation(
    db: Session,
    training_id: int,
    student_id: int,
    amount: float
) -> tuple[bool, str]:
    """
    Комплексная валидация для создания инвойса за тренировку
    
    Returns:
        (is_valid, error_message)
    """
    # Проверяем, что инвойс за эту тренировку ещё не создан
    existing_invoice = invoice_crud.get_training_invoice(db, training_id, student_id)
    if existing_invoice:
        return False, "Инвойс за эту тренировку уже существует"
    
    # Проверяем корректность суммы
    if not validate_payment_amount_positive(amount):
        return False, "Сумма инвойса должна быть положительной"
    
    return True, "" 