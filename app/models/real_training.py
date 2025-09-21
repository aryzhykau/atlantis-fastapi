from datetime import datetime
from sqlalchemy import Column, Integer, Date, Time, ForeignKey, Boolean, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
from enum import Enum

# Константа для безопасной отмены тренировки (в часах)
SAFE_CANCELLATION_HOURS = 24

class AttendanceStatus(str, Enum):
    # Базовые статусы посещения
    PRESENT = "PRESENT"              # Присутствовал
    ABSENT = "ABSENT"                # Отсутствовал (не пришел)
    
    # Статусы отмены
    CANCELLED_SAFE = "CANCELLED_SAFE"         # Отменен своевременно (>12ч, без штрафа)
    CANCELLED_PENALTY = "CANCELLED_PENALTY"   # Отменен поздно (<12ч, со штрафом)
    
    # Дополнительные статусы
    REGISTERED = "REGISTERED"        # Зарегистрирован, ждет тренировки
    WAITLIST = "WAITLIST"           # В листе ожидания (если есть ограничения)

class RealTraining(Base):
    __tablename__ = "real_trainings"

    id = Column(Integer, primary_key=True, index=True)
    training_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    responsible_trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("training_templates.id"), nullable=True)
    is_template_based = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)  # Время когда тренировка была обработана (процессинг)
    trainer_salary_eligible = Column(Boolean, nullable=True, default=True)  # Имеет ли право тренер на зарплату за эту тренировку
    is_salary_processed = Column(Boolean, default=False)  # Зарплата обработана

    # Relationships
    trainer = relationship("User", back_populates="real_trainings")
    training_type = relationship("TrainingType", back_populates="real_trainings")
    template = relationship("TrainingTemplate", back_populates="real_trainings")
    students = relationship("RealTrainingStudent", back_populates="real_training", cascade="all, delete-orphan")

class RealTrainingStudent(Base):
    __tablename__ = "real_training_students"

    id = Column(Integer, primary_key=True, index=True)
    real_training_id = Column(Integer, ForeignKey("real_trainings.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    template_student_id = Column(Integer, ForeignKey("training_client_templates.id"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("student_subscriptions.id"), nullable=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    attendance_marked_at = Column(DateTime, nullable=True)
    attendance_marked_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notification_time = Column(DateTime, nullable=True)
    requires_payment = Column(Boolean, nullable=True, default=True)
    session_deducted = Column(Boolean, default=False)

    # Relationships
    real_training = relationship("RealTraining", back_populates="students")
    student = relationship("Student", back_populates="real_trainings")
    template_student = relationship("TrainingStudentTemplate", back_populates="real_trainings")
    attendance_marked_by = relationship("User", foreign_keys=[attendance_marked_by_id])
    subscription = relationship("StudentSubscription", back_populates="real_trainings") 