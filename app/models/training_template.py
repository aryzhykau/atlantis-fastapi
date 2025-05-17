from sqlalchemy import Boolean, Column, Integer, String, Time, ForeignKey, DateTime, Date, Index
from sqlalchemy.orm import relationship

from app.database import Base


class TrainingStudentTemplate(Base):
    __tablename__ = "training_client_templates"

    id = Column(Integer, primary_key=True, index=True)
    training_template_id = Column(Integer, ForeignKey("training_templates.id"), nullable=False)
    is_frozen = Column(Boolean, default=False, nullable=False)
    start_date = Column(Date, nullable=False)
    freeze_start_date = Column(Date, nullable=True)
    freeze_duration_days = Column(Integer, nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    linked_training_template = relationship("TrainingTemplate", back_populates="assigned_students")
    student = relationship("Student", backref="training_templates")
    real_trainings = relationship("RealTrainingStudent", back_populates="template_student")


class TrainingTemplate(Base):
    __tablename__ = "training_templates"

    id = Column(Integer, primary_key=True, index=True)
    day_number = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    responsible_trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)

    assigned_students = relationship("TrainingStudentTemplate", back_populates="linked_training_template")
    training_type = relationship("TrainingType", backref="training_templates")
    responsible_trainer = relationship("User", backref="training_templates")
    real_trainings = relationship("RealTraining", back_populates="template")

    __table_args__ = (
        Index('idx_day_time', 'day_number', 'start_time'),
    )






