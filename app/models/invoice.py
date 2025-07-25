from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Float, Boolean, String, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base


class InvoiceStatus(str, Enum):
    """Статусы инвойса"""
    UNPAID = "UNPAID"  # Неоплачен
    PAID = "PAID"  # Оплачен
    CANCELLED = "CANCELLED"  # Отменен


class InvoiceType(str, Enum):
    """Типы инвойса"""
    SUBSCRIPTION = "SUBSCRIPTION"  # Оплата абонемента
    TRAINING = "TRAINING"  # Оплата разовой тренировки
    LATE_CANCELLATION_FEE = "LATE_CANCELLATION_FEE"  # Штраф за позднюю отмену


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Клиент (плательщик)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # Студент (опционально, для информации)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)  # Абонемент (только для инвойсов типа SUBSCRIPTION)
    training_id = Column(Integer, ForeignKey("real_trainings.id"), nullable=True)  # Тренировка (только для инвойсов типа TRAINING)
    student_subscription_id = Column(Integer, ForeignKey("student_subscriptions.id"), nullable=True) # Конкретный абонемент студента

    # Основные поля
    type = Column(SQLEnum(InvoiceType), nullable=False)  # Тип инвойса
    amount = Column(Float, nullable=False)  # Сумма
    description = Column(String, nullable=False)  # Описание/причина
    
    # Статус и даты
    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.UNPAID)  # Статус
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)  # Дата создания
    paid_at = Column(DateTime(timezone=True), nullable=True)  # Дата оплаты
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # Дата отмены
    
    # Связи с пользователями
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто отменил
    
    # Флаг автопродления
    is_auto_renewal = Column(Boolean, default=False)  # Создан ли автоматически для автопродления

    # Relationships
    client = relationship("User", foreign_keys=[client_id], backref="invoices")
    student = relationship("Student", backref="student_invoices")
    subscription = relationship("Subscription", backref="invoices")
    training = relationship("RealTraining", backref="invoices")
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    student_subscription = relationship("StudentSubscription", foreign_keys=[student_subscription_id])

    def __repr__(self):
        return f"<Invoice(id={self.id}, client_id={self.client_id}, type={self.type}, amount={self.amount}, status={self.status})>"
