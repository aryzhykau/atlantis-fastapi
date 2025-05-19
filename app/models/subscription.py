from datetime import date, datetime, timedelta

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, case, func
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.hybrid import hybrid_property

from app.database import Base  # Убедитесь, что Base импортируется из вашего настроенного проекта


class Subscription(Base):
    __tablename__ = "subscriptions"  # Название таблицы

    id = Column(Integer, primary_key=True, index=True)  # Первичный ключ
    name = Column(String, nullable=False)  # Название абонемента
    price = Column(Float, nullable=False)  # Стоимость
    number_of_sessions = Column(Integer, nullable=False)  # Количество тренировок
    validity_days = Column(Integer, nullable=False)  # Срок действия в днях
    is_active = Column(Boolean, default=True)  # Активность абонемента


# Ассоциативная таблица для связи студентов и абонементов
class StudentSubscription(Base):
    __tablename__ = "student_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)

    start_date = Column(DateTime(timezone=True), nullable=False)  # Дата начала подписки
    end_date = Column(DateTime(timezone=True), nullable=False)  # Дата окончания подписки
    is_auto_renew = Column(Boolean, default=False)  # Включено ли автопродление
    freeze_start_date = Column(DateTime(timezone=True), nullable=True)  # Начало периода заморозки
    freeze_end_date = Column(DateTime(timezone=True), nullable=True)  # Конец периода заморозки
    
    # Учет тренировок
    sessions_left = Column(Integer, nullable=False)  # Оставшиеся тренировки
    transferred_sessions = Column(Integer, default=0)  # Перенесенные тренировки (максимум 3)
    
    # Автопродление
    auto_renewal_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # Инвойс на автопродление

    # Relationships
    student = relationship("Student", backref="student_subscriptions")
    subscription = relationship("Subscription", backref="student_subscriptions")
    auto_renewal_invoice = relationship("Invoice", foreign_keys=[auto_renewal_invoice_id])
    real_trainings = relationship("RealTrainingStudent", back_populates="subscription")

    @hybrid_property
    def status(self):
        """Вычисляет статус абонемента с учетом временных зон"""
        current_time = datetime.now(tz=self.end_date.tzinfo)
        
        if (self.freeze_start_date and self.freeze_end_date and
            current_time >= self.freeze_start_date and
            current_time <= self.freeze_end_date):
            return "frozen"
        
        if current_time > self.end_date:
            return "expired"
        
        return "active"

    @status.expression
    def status(cls):
        """SQL expression для status с учетом временных зон"""
        return case(
            (
                (cls.freeze_start_date.isnot(None)) &
                (cls.freeze_end_date.isnot(None)) &
                (func.now() >= cls.freeze_start_date) &
                (func.now() <= cls.freeze_end_date),
                "frozen"
            ),
            (func.now() > cls.end_date, "expired"),
            else_="active"
        )

    @hybrid_property
    def computed_end_date(self):
        """Пересчитанная дата окончания, добавляющая замороженные дни."""
        subscription = self.subscription
        if not subscription:
            raise ValueError("Subscription definition is missing for this entry")

        validity_period = timedelta(days=subscription.validity_days)
        original_end_date = self.start_date + validity_period

        if self.freeze_start_date and self.freeze_end_date:
            freeze_days = (self.freeze_end_date - self.freeze_start_date).days
            return original_end_date + timedelta(days=freeze_days)

        return original_end_date



