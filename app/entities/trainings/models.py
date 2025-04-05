from sqlalchemy import Column, Integer, ForeignKey, Time, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_date = Column(DateTime, nullable=False)
    training_time = Column(Time, nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    trainer = relationship("User", backref="trainings")
    clients = relationship("TrainingClient", backref="training")


class TrainingClient(Base):
    __tablename__ = "training_clients"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    covered_by_subscription = Column(Boolean, nullable=False, default=False)
    trial_training = Column(Boolean, nullable=False, default=False)

    client = relationship("User", backref="training_clients")

    __table_args__ = (
        UniqueConstraint('training_id', 'client_id', name='unique_training_client'),
    )
