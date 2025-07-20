from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    """Модель платежа (только наличные)"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    description = Column(String, nullable=True)
    registered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(String, nullable=True)

    # Relationships
    client = relationship("User", foreign_keys=[client_id], backref="payments")
    registered_by = relationship("User", foreign_keys=[registered_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    payment_history = relationship("PaymentHistory", back_populates="payment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payment(id={self.id}, client_id={self.client_id}, amount={self.amount})>" 