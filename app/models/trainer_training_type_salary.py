
from sqlalchemy import Column, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class TrainerTrainingTypeSalary(Base):
    __tablename__ = "trainer_training_type_salaries"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    salary = Column(Float, nullable=False)

    trainer = relationship("User", back_populates="training_type_salaries")
    training_type = relationship("TrainingType", back_populates="trainer_salaries")

    __table_args__ = (
        UniqueConstraint(
            "trainer_id", "training_type_id", name="uq_trainer_training_type"
        ),
    )
