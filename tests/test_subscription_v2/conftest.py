"""Фикстуры специфичные для тестов подписок v2."""
from datetime import date, datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from app.models import Subscription, StudentSubscription
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.real_training import RealTraining, RealTrainingStudent, AttendanceStatus
from app.models.training_type import TrainingType
from app.models.system_settings import SystemSettings
from app.models.user import User, UserRole
from app.models.student import Student


@pytest.fixture
def sub_v2_template(db_session: Session) -> Subscription:
    """Шаблон абонемента v2: 2 раза в неделю, 5000 руб."""
    sub = Subscription(
        name="Абонемент 2×/нед",
        price=5000.0,
        number_of_sessions=8,   # legacy поле
        validity_days=30,        # legacy поле
        is_active=True,
        sessions_per_week=2,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


@pytest.fixture
def sub_v2_template_3pw(db_session: Session) -> Subscription:
    """Шаблон абонемента v2: 3 раза в неделю."""
    sub = Subscription(
        name="Абонемент 3×/нед",
        price=7000.0,
        number_of_sessions=12,
        validity_days=30,
        is_active=True,
        sessions_per_week=3,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


@pytest.fixture
def system_settings_seeded(db_session: Session):
    """Инициализирует системные настройки в БД."""
    for key, value in [("makeup_window_days", "90"), ("debt_behavior", "HIGHLIGHT_ONLY")]:
        existing = db_session.query(SystemSettings).filter(SystemSettings.key == key).first()
        if not existing:
            db_session.add(SystemSettings(key=key, value=value))
    db_session.commit()


@pytest.fixture
def training_type_sub_only(db_session: Session) -> TrainingType:
    """Тип тренировки с is_subscription_only=True."""
    tt = TrainingType(
        name="Групповая v2",
        is_subscription_only=True,
        price=2000.0,
        color="#123456",
        is_active=True,
        max_participants=15,
    )
    db_session.add(tt)
    db_session.commit()
    db_session.refresh(tt)
    return tt


@pytest.fixture
def training_type_open(db_session: Session) -> TrainingType:
    """Тип тренировки с is_subscription_only=False."""
    tt = TrainingType(
        name="Открытая v2",
        is_subscription_only=False,
        price=1500.0,
        color="#654321",
        is_active=True,
        max_participants=10,
    )
    db_session.add(tt)
    db_session.commit()
    db_session.refresh(tt)
    return tt


@pytest.fixture
def client_with_balance(db_session: Session) -> User:
    """Клиент с балансом 10 000 руб."""
    user = User(
        first_name="Rich",
        last_name="Client",
        date_of_birth=date(1990, 1, 1),
        email="rich.client.v2@example.com",
        phone_country_code="7",
        phone_number="9001112233",
        role=UserRole.CLIENT,
        balance=10000.0,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client_no_balance(db_session: Session) -> User:
    """Клиент с нулевым балансом."""
    user = User(
        first_name="Poor",
        last_name="Client",
        date_of_birth=date(1992, 3, 3),
        email="poor.client.v2@example.com",
        phone_country_code="7",
        phone_number="9002223344",
        role=UserRole.CLIENT,
        balance=0.0,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_rich(db_session: Session, client_with_balance: User) -> Student:
    """Активный студент с богатым клиентом."""
    s = Student(
        client_id=client_with_balance.id,
        first_name="Rich",
        last_name="Student",
        date_of_birth=date(2000, 5, 10),
        is_active=True,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def student_poor(db_session: Session, client_no_balance: User) -> Student:
    """Активный студент с нулевым балансом клиента."""
    s = Student(
        client_id=client_no_balance.id,
        first_name="Poor",
        last_name="Student",
        date_of_birth=date(2001, 7, 15),
        is_active=True,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def make_student_sub_v2(
    db_session: Session,
    student_id: int,
    subscription: Subscription,
    start_date: date,
    end_date: date,
    is_auto_renew: bool = False,
    payment_due_date: date = None,
    is_prorated: bool = False,
) -> StudentSubscription:
    """Вспомогательная функция для создания StudentSubscription v2."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
    sub = StudentSubscription(
        student_id=student_id,
        subscription_id=subscription.id,
        start_date=start_dt,
        end_date=end_dt,
        is_auto_renew=is_auto_renew,
        sessions_left=0,
        payment_due_date=payment_due_date,
        is_prorated=is_prorated,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def make_real_training(
    db_session: Session,
    training_date: date,
    training_type: TrainingType,
    trainer_id: int,
) -> RealTraining:
    from datetime import time
    rt = RealTraining(
        training_date=training_date,
        start_time=time(10, 0),
        responsible_trainer_id=trainer_id,
        training_type_id=training_type.id,
        is_template_based=False,
    )
    db_session.add(rt)
    db_session.commit()
    db_session.refresh(rt)
    return rt


def make_rts(
    db_session: Session,
    real_training: RealTraining,
    student_id: int,
    status: AttendanceStatus,
    student_sub_id: int = None,
) -> RealTrainingStudent:
    rts = RealTrainingStudent(
        real_training_id=real_training.id,
        student_id=student_id,
        subscription_id=student_sub_id,
        status=status,
    )
    db_session.add(rts)
    db_session.commit()
    db_session.refresh(rts)
    return rts
