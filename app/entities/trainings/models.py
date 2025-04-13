import logging

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base

logger = logging.getLogger(__name__)

class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_datetime = Column(DateTime(timezone=True), nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    trainer = relationship("User", backref="trainings")
    clients = relationship("TrainingClient", back_populates="training")


    __table_args__ = (
        UniqueConstraint(
            'trainer_id', 'training_datetime', name='unique_trainer_training_datetime'
        ),
    )


class TrainingClient(Base):
    __tablename__ = "training_clients"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    trial_training = Column(Boolean, nullable=False, default=False, server_default="false")

    client = relationship("User", backref="training_clients")
    training = relationship("Training", back_populates="clients")


    __table_args__ = (
            UniqueConstraint('training_id', 'client_id', name='unique_training_client'),
        )
