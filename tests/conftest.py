from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.models.user import UserRole
from app.models import (
    User,
    TrainingType,
    Subscription,
    Student,
    StudentSubscription,
    Payment,
    Invoice,
    InvoiceStatus,
    PaymentHistory,
    InvoiceType,
    RealTraining
)
from app.auth.jwt_handler import create_access_token

# URL для тестовой базы данных (SQLite в оперативной памяти)
DATABASE_URL = "sqlite:///./test_database.db"

@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для работы с одной общей сессией базы данных внутри каждого теста.
    """

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    test_user = User(
        first_name="Andrei",
        last_name="Ryzhykau",
        date_of_birth=date(1997, 6, 14),
        email="rorychan0697@gmail.com",
        phone="0940597865",
        role=UserRole.ADMIN,
        is_authenticated_with_google=True,
    )
    session.add(test_user)
    session.commit()
    session.refresh(test_user)

    try:
        admin = session.query(User).filter(User.email == "rorychan0697@gmail.com").first()
        if admin:
            yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client):
    """
    Получение токенов (замените фейковую аутентификацию на реальную, если требуется).
    """
    return {"Authorization": "Bearer dev_token"}


@pytest.fixture
def client(db_session):
    """
    Тестовый клиент FastAPI с переопределением зависимости `get_db` для работы с тестовой базой данных.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_admin(db_session):
    """
    Возвращает тестового администратора.
    """
    return db_session.query(User).filter(User.email == "rorychan0697@gmail.com").first()


@pytest.fixture
def test_client(db_session):
    """
    Создает тестового клиента в базе данных.
    """
    test_client = User(
        first_name="John",
        last_name="Example",
        date_of_birth=date(1998, 11, 23),
        email="testclient@example.com",
        phone="9876543210",
        role=UserRole.CLIENT,
        balance=0,
        whatsapp_number="1234567890",
        is_active=True,
    )
    db_session.add(test_client)
    db_session.commit()
    db_session.refresh(test_client)
    return test_client


@pytest.fixture
def test_student(db_session, test_client):
    """
    Создает тестового студента в базе данных.
    """
    student = Student(
        client_id=test_client.id,
        first_name="Test",
        last_name="Student",
        date_of_birth=date(2000, 1, 1),
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def test_subscription(db_session):
    """
    Создает тестовый абонемент в базе данных.
    """
    subscription = Subscription(
        name="Test Subscription",
        price=100.0,
        number_of_sessions=8,
        validity_days=30,
        is_active=True
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def test_student_subscription(db_session, test_student, test_subscription):
    """
    Создает тестовую подписку студента в базе данных.
    """
    student_subscription = StudentSubscription(
        student_id=test_student.id,
        subscription_id=test_subscription.id,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        sessions_left=test_subscription.number_of_sessions,
        transferred_sessions=0,
        is_auto_renew=False
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)
    return student_subscription


@pytest.fixture
def test_payment(db_session, test_client, test_admin):
    """
    Создает тестовый платеж в базе данных.
    """
    payment = Payment(
        client_id=test_client.id,
        amount=100.0,
        description="Test payment",
        registered_by_id=test_admin.id
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment


@pytest.fixture
def test_invoice(db_session: Session, test_client: User, test_subscription: Subscription) -> Invoice:
    """Создает тестовый неоплаченный инвойс"""
    invoice = Invoice(
        client_id=test_client.id,
        subscription_id=test_subscription.id,
        amount=100.0,
        description="Test invoice for payment",
        status=InvoiceStatus.UNPAID,
        type=InvoiceType.SUBSCRIPTION,
        created_by_id=test_client.id,
        is_auto_renewal=False
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def test_payment_history(db_session, test_payment, test_client):
    """
    Создает тестовую запись в истории платежей.
    """
    history = PaymentHistory(
        payment_id=test_payment.id,
        client_id=test_client.id,
        amount=test_payment.amount,
        balance_before=0.0,
        balance_after=test_payment.amount,
        operation_type="PAYMENT"
    )
    db_session.add(history)
    db_session.commit()
    db_session.refresh(history)
    return history


@pytest.fixture
def test_monthly_stats(db_session, test_student):
    """
    Создает тестовую месячную статистику студента.
    """
    stats = StudentMonthlyStats(
        student_id=test_student.id,
        month=datetime.utcnow().replace(day=1),
        total_sessions=8,
        attended_sessions=6,
        cancelled_sessions=1,
        transferred_sessions=1
    )
    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)
    return stats


@pytest.fixture
def test_training(db_session, test_admin):
    """
    Создает тестовую тренировку в базе данных.
    """
    training = RealTraining(
        training_date=date.today(),
        start_time=datetime.now().time(),
        responsible_trainer_id=test_admin.id,
        training_type_id=1
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    return training


@pytest.fixture
def create_test_client(db_session):
    """Создает тестового клиента в базе данных."""
    client = User(
        first_name="Test",
        last_name="Client",
        date_of_birth=date(1990, 1, 1),
        email="test.client@example.com",
        phone="1234567891",
        whatsapp_number="1234567891",
        role=UserRole.CLIENT,
        balance=0,
        is_active=True
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def trainer_auth_headers(trainer):
    """
    Получение токенов для тренера
    """
    token_data = {
        "sub": trainer.email,
        "id": trainer.id,
        "role": UserRole.TRAINER.value
    }
    access_token = create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


