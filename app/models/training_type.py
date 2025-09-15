from sqlalchemy import Boolean, Column, Float, Integer, String, Time, Enum, text
from sqlalchemy.orm import relationship
from app.database import Base


class TrainingType(Base):
    __tablename__ = "training_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_subscription_only = Column(Boolean, default=False)
    price = Column(Float, nullable=True)
    color = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    max_participants = Column(Integer, nullable=False, server_default=text("4"))

    # Cancellation policy fields (added by migration 17fb6047d5c3)
    cancellation_mode = Column(
        Enum('FIXED', 'FLEXIBLE', name='cancellationmode'),
        nullable=False,
        server_default=text("'FLEXIBLE'")
    )
    safe_cancel_time_morning = Column(Time(), nullable=True)
    safe_cancel_time_evening = Column(Time(), nullable=True)
    safe_cancel_time_morning_prev_day = Column(Boolean(), nullable=False, server_default=text('false'))
    safe_cancel_time_evening_prev_day = Column(Boolean(), nullable=False, server_default=text('false'))
    safe_cancel_hours = Column(Integer, nullable=True, server_default=text('24'))

    # Relationships
    real_trainings = relationship("RealTraining", back_populates="training_type")
    trainer_salaries = relationship("TrainerTrainingTypeSalary", back_populates="training_type")

    def __repr__(self):
        return f"<TrainingType(id={self.id}, name={self.name}, subscription_only={self.is_subscription_only}, is_active={self.is_active})>"