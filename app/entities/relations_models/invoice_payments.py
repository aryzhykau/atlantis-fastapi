from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean, DECIMAL
from app.database import Base


class InvoicePayments(Base):
    __tablename__ = 'invoice_payments'

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False)
    amount = Column(DECIMAL, nullable=False)
