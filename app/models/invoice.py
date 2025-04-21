from sqlalchemy import Column, Integer, ForeignKey, DateTime, Float, Boolean, String
from sqlalchemy.orm import relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)  # Студенты
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)  # Абонемент

    # Тип инвойса: 'subscription' или 'training'
    type = Column(String, nullable=False)

    payment_date = Column(DateTime(timezone=True), nullable=False)  # Дата оплаты
    amount = Column(Float, nullable=False)  # Сумма
    is_paid = Column(Boolean, default=False, nullable=False)  # Оплачен ли инвойс

    # Связи
    student = relationship("Student", backref="invoices")
    subscription = relationship("Subscription", backref="invoices")
