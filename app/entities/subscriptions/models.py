from sqlalchemy import Column, Integer, DECIMAL, DateTime, func, String, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean, nullable=False, default=True)
    title = Column(String(255), nullable=False, unique=True)
    duration = Column(Integer, nullable=False)
    total_sessions = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    clients = relationship("User", secondary="client_subscriptions", back_populates="subscription")