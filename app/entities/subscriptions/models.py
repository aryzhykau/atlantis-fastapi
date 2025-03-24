from sqlalchemy import Column, Integer, DECIMAL, TIMESTAMP, func, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from app.database import Base


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean, nullable=False, default=True)
    title = Column(String(255), nullable=False, unique=True)
    total_sessions = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)