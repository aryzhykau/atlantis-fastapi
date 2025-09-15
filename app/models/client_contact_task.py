from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ClientContactReason(PyEnum):
    NEW_CLIENT = "NEW_CLIENT"
    RETURNED = "RETURNED"


class ClientContactStatus(PyEnum):
    PENDING = "PENDING"
    DONE = "DONE"


class ClientContactTask(Base):
    __tablename__ = "client_contact_tasks"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Enum(ClientContactReason), nullable=False)
    status = Column(Enum(ClientContactStatus), nullable=False, default=ClientContactStatus.PENDING)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    done_at = Column(DateTime(timezone=True), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    client = relationship("User", foreign_keys=[client_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])



