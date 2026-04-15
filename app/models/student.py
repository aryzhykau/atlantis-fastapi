from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from app.database import Base


# Модель студента
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)  # Имя
    last_name = Column(String, nullable=False)  # Фамилия
    date_of_birth = Column(Date, nullable=False)  # Дата рождения
    client_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Клиент, к которому привязан студент
    is_active = Column(Boolean, nullable=False, default=True)
    deactivation_date = Column(DateTime, nullable=True)

    # Связь с клиентом
    client = relationship("User", backref=backref("students", passive_deletes=True))

    # Связь many-to-many с абонементами через таблицу association
    subscriptions = relationship(
        "Subscription", secondary="student_subscriptions", backref="students", viewonly=True
    )

    # Один активный абонемент
    active_subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    active_subscription = relationship("Subscription", foreign_keys=[active_subscription_id])

    # Связь с реальными тренировками
    real_trainings = relationship("RealTrainingStudent", foreign_keys="RealTrainingStudent.student_id", back_populates="student")

    # Пробное занятие
    trial_used_at = Column(DateTime, nullable=True)
    trial_real_training_student_id = Column(Integer, ForeignKey("real_training_students.id"), nullable=True)

    @property
    def has_unpaid_invoice(self) -> bool:
        """True если у студента есть хотя бы один UNPAID инвойс."""
        from sqlalchemy.orm import object_session
        from app.models.invoice import Invoice, InvoiceStatus
        session = object_session(self)
        if not session:
            return False
        return session.query(Invoice).filter(
            Invoice.student_id == self.id,
            Invoice.status == InvoiceStatus.UNPAID,
        ).first() is not None

    def __repr__(self):
        return f"<Student(id={self.id}, first_name={self.first_name}, last_name={self.last_name})>"
