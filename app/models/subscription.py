from datetime import date, timedelta

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

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

    student = relationship("Student", backref="student_subscriptions")  # Обратная связь со студентами
    subscription = relationship("Subscription", backref="student_subscriptions")  # Обратная связь с абонементами


    # Гибридное свойство для статуса подписки
    @hybrid_property
    def status(self):
        """Вычисляет статус подписки: 'active', 'expired', 'frozen'."""
        today = date.today()
        if self.freeze_start_date and self.freeze_end_date:
            if self.freeze_start_date <= today <= self.freeze_end_date:
                return "frozen"
        elif self.end_date < today:
            return "expired"
        return "active"

    # SQL-выражение для гибридного свойства
    @hybrid_property
    def computed_end_date(self):
        """Пересчитанная дата окончания, добавляющая замороженные дни."""
        subscription = self.subscription
        if not subscription:
            raise ValueError("Subscription definition is missing for this entry")

        # Длительность действия подписки
        validity_period = timedelta(days=subscription.validity_days)
        original_end_date = self.start_date + validity_period

        # Учитываем заморозку
        if self.freeze_start_date and self.freeze_end_date:
            freeze_days = (self.freeze_end_date - self.freeze_start_date).days
            return original_end_date + timedelta(days=freeze_days)

        return original_end_date



