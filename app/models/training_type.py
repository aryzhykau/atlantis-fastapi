from sqlalchemy import Boolean, Column, Float, Integer, String, text
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

    # Relationships
    real_trainings = relationship("RealTraining", back_populates="training_type")
    trainer_salaries = relationship("TrainerTrainingTypeSalary", back_populates="training_type")

    def __repr__(self):
        return f"<TrainingType(id={self.id}, name={self.name}, subscription_only={self.is_subscription_only}, is_active={self.is_active})>"