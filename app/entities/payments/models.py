from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    payment_date = Column(DateTime(timezone=True))
    client = relationship("User", back_populates="payments")


