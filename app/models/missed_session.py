from datetime import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MissedSession(Base):
    __tablename__ = "missed_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Кто пропустил и в рамках какого абонемента
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    student_subscription_id = Column(Integer, ForeignKey("student_subscriptions.id"), nullable=False)

    # Конкретная запись на тренировку (пропуск)
    real_training_student_id = Column(Integer, ForeignKey("real_training_students.id"), nullable=False, unique=True)

    # Уважительная причина
    is_excused = Column(Boolean, default=False, nullable=False)
    excused_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    excused_at = Column(DateTime(timezone=True), nullable=True)

    # Дедлайн отработки (NULL до ручного excusing)
    makeup_deadline_date = Column(Date, nullable=True)

    # Отработка
    made_up_at = Column(DateTime(timezone=True), nullable=True)
    made_up_real_training_student_id = Column(Integer, ForeignKey("real_training_students.id"), nullable=True)

    # Аудит
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Relationships
    student = relationship("Student", backref="missed_sessions")
    student_subscription = relationship("StudentSubscription", backref="missed_sessions")
    real_training_student = relationship(
        "RealTrainingStudent",
        foreign_keys=[real_training_student_id],
        backref="missed_session",
    )
    made_up_real_training_student = relationship(
        "RealTrainingStudent",
        foreign_keys=[made_up_real_training_student_id],
    )
    excused_by = relationship("User", foreign_keys=[excused_by_id])
