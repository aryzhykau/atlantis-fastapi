from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, Float, Table
from sqlalchemy.orm import relationship, backref
from app.database import Base


# Модель студента
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)  # Имя
    last_name = Column(String, nullable=False)  # Фамилия
    date_of_birth = Column(Date, nullable=False)  # Дата рождения
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Клиент, к которому привязан студент

    # Связь с клиентом
    client = relationship("User", backref=backref("students", cascade="all, delete"))

    # Связь many-to-many с абонементами через таблицу association
    subscriptions = relationship(
        "Subscription", secondary="student_subscriptions", backref="students"
    )

    # Один активный абонемент
    active_subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    active_subscription = relationship("Subscription", foreign_keys=[active_subscription_id])

    def __repr__(self):
        return f"<Student(id={self.id}, first_name={self.first_name}, last_name={self.last_name})>"
