from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from enum import Enum

from app.database import Base


class OperationType(str, Enum):
    """Типы операций с платежами"""
    PAYMENT = "PAYMENT"  # Регистрация платежа
    CANCELLATION = "CANCELLATION"  # Отмена платежа
    INVOICE_PAYMENT = "INVOICE_PAYMENT"  # Оплата инвойса из баланса


class PaymentHistory(Base):
    """История платежей и изменений баланса"""
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)  # Может быть null для операций с инвойсами
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # ID инвойса (для операций оплаты инвойса)
    operation_type = Column(String, nullable=False)  # Тип операции (payment/cancellation/invoice_payment)
    amount = Column(Float, nullable=False)  # Сумма операции
    balance_before = Column(Float, nullable=False)  # Баланс до операции
    balance_after = Column(Float, nullable=False)  # Баланс после операции
    description = Column(String, nullable=True)  # Описание операции или причина отмены
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто создал запись

    # Relationships
    client = relationship("User", foreign_keys=[client_id])
    payment = relationship("Payment", back_populates="payment_history", foreign_keys=[payment_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<PaymentHistory(id={self.id}, payment_id={self.payment_id}, operation={self.operation_type}, amount={self.amount})>" 