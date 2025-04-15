from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, and_, \
    func
from sqlalchemy.orm import relationship, column_property

from app.database import Base


class UserRoleEnum(str, Enum):  # Наследуем str, чтобы хранилось как строка
    CLIENT = "CLIENT"
    TRAINER = "TRAINER"
    ADMIN = "ADMIN"


class ClientSubscription(Base):
    __tablename__ = 'client_subscriptions'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, nullable=False, default=True, )
    sessions_left = Column(Integer, nullable=True)
    client = relationship("User", backref="subscriptions")
    subscription = relationship("Subscription", backref="client_subscriptions")

    is_active = column_property(end_date >= func.now())



    def __repr__(self):
        return f"<ClientSubscription(id={self.id}, client_id={self.client_id}, subscription_id={self.subscription_id}, " \
               f"start_date={self.start_date}, end_date={self.end_date}, active={self.active}, " \
               f"sessions_left={self.sessions_left}, invoice_id={self.invoice_id})>"




# Основная модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, index=True)
    whatsapp = Column(String, nullable=True)
    salary = Column(Integer, nullable=True)
    has_trial = Column(Boolean, nullable=True, default=None)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    fixed_salary = Column(Boolean, nullable=True)
    balance = Column(Integer, nullable=True)
    parent_name = Column(String, nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    google_authenticated = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    active_subscription = relationship("ClientSubscription", primaryjoin=and_(
            id == ClientSubscription.client_id,  # Join condition
            ClientSubscription.is_active == True # Fetch only where active=True
        ),
        lazy="select",  # Load the relationship lazily when accessed
        uselist=False)


    role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"
    ), nullable=False)  # Может быть "admin", "client", "trainer"



