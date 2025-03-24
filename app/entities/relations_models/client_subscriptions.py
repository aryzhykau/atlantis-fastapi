from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from app.database import Base


class ClientSubscription(Base):
    __tablename__ = 'client_subscriptions'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    sessions_left = Column(Integer, nullable=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)

    def __repr__(self):
        return f"<ClientSubscription(id={self.id}, client_id={self.client_id}, subscription_id={self.subscription_id}, " \
               f"start_date={self.start_date}, end_date={self.end_date}, active={self.active}, " \
               f"sessions_left={self.sessions_left}, invoice_id={self.invoice_id})>"