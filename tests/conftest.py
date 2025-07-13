from datetime import date, datetime, timedelta, time, timezone
import os

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
    RealTraining,
    RealTrainingStudent
)
from app.models.real_training import AttendanceStatus
from app.auth.jwt_handler import create_access_token

# URL для тестовой базы данных (SQLite в оперативной памяти)
DATABASE_URL = "sqlite:///./test_database.db"

# Глобальная переменная для отслеживания первого теста
_first_test = True

@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для работы с одной общей сессией базы данных внутри каждого теста.
    """
    global _first_test
    
    # Удаляем файл базы данных только перед первым тестом
    if _first_test and os.path.exists("test_database.db"):
        os.remove("test_database.db")
        _first_test = False

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
def test_trainer(db_session: Session) -> User:
    """
    Создает тестового тренера в базе данных.
    """
    trainer = User(
        first_name="Тестовый",
        last_name="Тренер",
        email="fittesttrainer@example.com",
        phone="1234567891",
        date_of_birth=date(1990, 5, 15),
        role=UserRole.TRAINER,
        is_active=True,
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    return trainer


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


@pytest.fixture
def test_training_type_subscription(db_session):
    """
    Создает тестовый тип тренировки, требующий абонемент
    """
    training_type = TrainingType(
        name="Йога",
        is_subscription_only=True,
        price=2000.0,
        color="#FF5733",
        is_active=True,
        max_participants=10
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    return training_type


@pytest.fixture
def test_training_type_no_subscription(db_session):
    """
    Создает тестовый тип тренировки, не требующий абонемент
    """
    training_type = TrainingType(
        name="Пилатес",
        is_subscription_only=False,
        price=1500.0,
        color="#33FF57",
        is_active=True,
        max_participants=8
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    return training_type


@pytest.fixture
def test_second_trainer(db_session: Session) -> User:
    """
    Создает второго тестового тренера в базе данных.
    """
    trainer = User(
        first_name="Второй",
        last_name="Тренер",
        email="secondtrainer@example.com",
        phone="1234567892",
        date_of_birth=date(1985, 8, 20),
        role=UserRole.TRAINER,
        is_active=True,
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    return trainer


@pytest.fixture
def test_second_client(db_session):
    """
    Создает второго тестового клиента в базе данных.
    """
    test_client = User(
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1995, 5, 15),
        email="janedoe@example.com",
        phone="9876543211",
        role=UserRole.CLIENT,
        balance=5000.0,
        whatsapp_number="1234567891",
        is_active=True,
    )
    db_session.add(test_client)
    db_session.commit()
    db_session.refresh(test_client)
    return test_client


@pytest.fixture
def test_second_student(db_session, test_second_client):
    """
    Создает второго тестового студента в базе данных.
    """
    student = Student(
        client_id=test_second_client.id,
        first_name="Second",
        last_name="Student",
        date_of_birth=date(2001, 3, 15),
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def test_tomorrow_training(db_session, test_trainer, test_training_type_subscription):
    """
    Создает тестовую тренировку на завтра
    """
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(10, 0),  # 10:00
        responsible_trainer_id=test_trainer.id,
        training_type_id=test_training_type_subscription.id,
        is_template_based=False
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    return training


@pytest.fixture
def test_tomorrow_training_no_subscription(db_session, test_second_trainer, test_training_type_no_subscription):
    """
    Создает тестовую тренировку на завтра без требования абонемента
    """
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(11, 0),  # 11:00
        responsible_trainer_id=test_second_trainer.id,
        training_type_id=test_training_type_no_subscription.id,
        is_template_based=False
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    return training


@pytest.fixture
def cron_api_key():
    """
    Возвращает API ключ для cron эндпоинтов
    """
    return "test-cron-api-key-12345"


@pytest.fixture
def api_key_headers(cron_api_key):
    """
    Возвращает заголовки с API ключом для крон задач.
    """
    return {"X-API-Key": cron_api_key}


@pytest.fixture
def auth_headers_trainer(client, test_trainer):
    """
    Возвращает заголовки авторизации для тренера.
    """
    from app.auth.jwt_handler import create_access_token
    from app.schemas.user import UserRole
    
    token = create_access_token(
        data={"sub": str(test_trainer.id), "role": UserRole.TRAINER, "id": test_trainer.id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_student_training(db_session, test_tomorrow_training, test_student, test_student_subscription):
    """
    Создает связь студента с тренировкой (с абонементом)
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_student_training_no_subscription(db_session, test_tomorrow_training, test_student):
    """
    Создает связь студента с тренировкой (без абонемента)
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_student_training_safe_cancellation(db_session, test_tomorrow_training, test_student, test_student_subscription):
    """
    Создает связь студента с тренировкой с безопасной отменой
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id,
        status=AttendanceStatus.CANCELLED_SAFE,
        cancelled_at=datetime.utcnow() - timedelta(hours=15)  # 15 часов назад
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_student_training_penalty_cancellation(db_session, test_tomorrow_training, test_student, test_student_subscription):
    """
    Создает связь студента с тренировкой со штрафной отменой
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id,
        status=AttendanceStatus.CANCELLED_PENALTY,
        cancelled_at=datetime.utcnow() - timedelta(hours=2)  # 2 часа назад
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_student_training_penalty_cancellation_no_subscription(db_session, test_tomorrow_training, test_student):
    """
    Создает связь студента с тренировкой со штрафной отменой без абонемента
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=None,
        status=AttendanceStatus.CANCELLED_PENALTY,
        cancelled_at=datetime.utcnow() - timedelta(hours=2)  # 2 часа назад
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Фикстуры для тренировки БЕЗ требования абонемента
@pytest.fixture
def test_real_training_student_no_subscription_type(db_session, test_tomorrow_training_no_subscription, test_student):
    """
    Создает связь студента с тренировкой без требования абонемента
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training_no_subscription.id,
        student_id=test_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_real_training_student_no_subscription_type_with_subscription(db_session, test_tomorrow_training_no_subscription, test_student, test_student_subscription):
    """
    Создает связь студента с абонементом на тренировке без требования абонемента
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training_no_subscription.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_real_training_student_penalty_cancellation_no_subscription_type(db_session, test_tomorrow_training_no_subscription, test_student):
    """
    Создает связь студента с тренировкой без требования абонемента со штрафной отменой
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training_no_subscription.id,
        student_id=test_student.id,
        subscription_id=None,
        status=AttendanceStatus.CANCELLED_PENALTY,
        cancelled_at=datetime.utcnow() - timedelta(hours=2)  # 2 часа назад
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Фикстуры для второго студента на тренировке с абонементом
@pytest.fixture
def test_real_training_second_student_with_subscription(db_session, test_tomorrow_training, test_second_student, test_student_subscription):
    """
    Создает связь второго студента с абонементом на тренировке
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_second_student.id,
        subscription_id=test_student_subscription.id
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_real_training_second_student_without_subscription(db_session, test_tomorrow_training, test_second_student):
    """
    Создает связь второго студента без абонемента на тренировке
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_second_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Фикстуры для второго студента на тренировке без требования абонемента
@pytest.fixture
def test_real_training_second_student_no_subscription_type(db_session, test_tomorrow_training_no_subscription, test_second_student):
    """
    Создает связь второго студента с тренировкой без требования абонемента
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training_no_subscription.id,
        student_id=test_second_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Фикстуры для множественных студентов на одной тренировке
@pytest.fixture
def test_real_training_multiple_students(db_session, test_tomorrow_training, test_student, test_student_subscription, test_second_student):
    """
    Создает связи двух студентов на одной тренировке (первый с абонементом, второй без)
    """
    # Первый студент с абонементом
    student1_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id
    )
    db_session.add(student1_training)
    
    # Второй студент без абонемента
    student2_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_second_student.id,
        subscription_id=None
    )
    db_session.add(student2_training)
    db_session.commit()
    
    return [student1_training, student2_training]


# Фикстуры для отмененных тренировок
@pytest.fixture
def test_cancelled_training(db_session, test_trainer, test_training_type_subscription):
    """
    Создает отмененную тренировку на завтра
    """
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=time(12, 0),  # 12:00
        responsible_trainer_id=test_trainer.id,
        training_type_id=test_training_type_subscription.id,
        is_template_based=False,
        cancelled_at=datetime.utcnow(),
        cancellation_reason="Test cancellation"
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)
    return training


@pytest.fixture
def test_real_training_student_cancelled_training(db_session, test_cancelled_training, test_student):
    """
    Создает связь студента с отмененной тренировкой
    """
    student_training = RealTrainingStudent(
        real_training_id=test_cancelled_training.id,
        student_id=test_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Фикстуры для студентов с истекшими абонементами



@pytest.fixture
def test_real_training_student_expired_subscription(db_session, test_tomorrow_training, test_student, test_student_subscription_expired):
    """
    Создает связь студента с истекшим абонементом на тренировке
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription_expired.id
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Добавляем недостающие фикстуры
@pytest.fixture
def test_real_training_student_with_subscription(db_session, test_tomorrow_training, test_student, test_student_subscription):
    """
    Создает связь студента с абонементом на тренировке
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_real_training_student_without_subscription(db_session, test_tomorrow_training, test_student):
    """
    Создает связь студента без абонемента на тренировке
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=None
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


@pytest.fixture
def test_student_training_penalty_cancellation_with_subscription(db_session, test_tomorrow_training, test_student, test_student_subscription):
    """
    Создает связь студента с тренировкой со штрафной отменой с абонементом
    """
    student_training = RealTrainingStudent(
        real_training_id=test_tomorrow_training.id,
        student_id=test_student.id,
        subscription_id=test_student_subscription.id,
        status=AttendanceStatus.CANCELLED_PENALTY,
        cancelled_at=datetime.utcnow() - timedelta(hours=2)  # 2 часа назад
    )
    db_session.add(student_training)
    db_session.commit()
    db_session.refresh(student_training)
    return student_training


# Импортируем фикстуры для подписок
from .fixtures.subscription_fixtures import (
    test_subscription,
    test_student_subscription,
    test_auto_renewal_subscription,
    test_student_subscription_expired,
    test_frozen_subscription,
    test_expired_frozen_subscription,
    test_subscription_with_transferred_sessions,
    test_inactive_subscription
)





