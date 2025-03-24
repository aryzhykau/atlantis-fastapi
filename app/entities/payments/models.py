from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from app.database import Base



class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    payment_type = Column(String)  # "one_time", "trial", "subscription"
    payment_date = Column(Date)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    client = relationship("User", backref="payments")
    subscription = relationship("Subscription", backref="payments")


