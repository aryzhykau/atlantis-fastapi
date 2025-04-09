from enum import Enum

from sqlalchemy import Column, Integer, ForeignKey, Enum as SQLEnum, DateTime, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


class InvoiceTypeEnum(str, Enum):  # Наследуем str, чтобы хранилось как строка
    SINGLE = "SINGLE"
    SUBSCRIPTION = "SUBSCRIPTION"
    TRIAL = "TRIAL"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    invoice_type = Column(SQLEnum(InvoiceTypeEnum, name="invoice_type_enum"), nullable=False)
    # client_subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="invoices")

#