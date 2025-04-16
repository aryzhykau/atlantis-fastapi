from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, and_, \
    func
from sqlalchemy.orm import relationship, column_property

from app.database import Base

class ClientSubscription(Base):
    __tablename__ = 'client_subscriptions'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, nullable=False, default=True, )
    sessions_left = Column(Integer, nullable=False)
    client = relationship("Client", backref="subscriptions")
    subscription = relationship("Subscription", backref="client_subscriptions")
    is_active = column_property(end_date >= func.now())


    def __repr__(self):
        return f"<ClientSubscription(id={self.id}, client_id={self.client_id}, subscription_id={self.subscription_id}, " \
               f"start_date={self.start_date}, end_date={self.end_date}, active={self.active}, " \
               f"sessions_left={self.sessions_left}, invoice_id={self.invoice_id})>"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    has_trial = Column(Boolean, nullable=True, default=None)
    birth_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    active_subscription = relationship("ClientSubscription", primaryjoin=and_(
        id == ClientSubscription.client_id,  # Join condition
        ClientSubscription.is_active == True  # Fetch only where active=True
    ),
                                       lazy="select",  # Load the relationship lazily when accessed
                                       uselist=False)

    relative = relationship("User", back_populates="clients")
