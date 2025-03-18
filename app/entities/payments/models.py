from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from app.database import Base



class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    amount = Column(Float)
    payment_type = Column(String)  # "one_time", "trial", "subscription"
    payment_date = Column(Date)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    client = relationship("Client", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    active = Column(Boolean, nullable=False, default=True)
    total_sessions = Column(Integer)  # Общее количество занятий
    missed_sessions = Column(Integer)  # Пропущенные занятия
    trainings_from_old_subscription = Column(Integer, nullable=False, default=0)
    created_at = Column(Date, nullable=False)
    updated_at = Column(Date, nullable=False)

    client = relationship("Client", back_populates="subscriptions")
