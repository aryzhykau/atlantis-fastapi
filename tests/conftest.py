from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.models.user import UserRole
from app.models import User, TrainingType, Subscription, Student, StudentSubscription

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
    print("Получение сессии")
    print("Создание тестового админа")

    try:
        admin = session.query(User).filter(User.email == "rorychan0697@gmail.com").first()
        if admin:
            print("Admin created successfully")
            yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client):
    """
    Получение токенов (замените фейковую аутентификацию на реальную, если требуется).
    """
    # Используйте эндпоинт Google авторизации или замените на реальный токен
    return {"Authorization": "Bearer dev_token"}

@pytest.fixture
def client(db_session):
    """
    Тестовый клиент FastAPI с переопределением зависимости `get_db` для работы с тестовой базой данных.
    """
    print("Таблицы в базе перед переопределнием")
    print(db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall())
    def override_get_db():
        yield db_session


    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def create_test_client(db_session):
    """
    Создает тестового тренера в базе данных.
    """

    # Данные для тестового тренера
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
    yield test_client  # Возвращаем объект тренера для использования в тестах

    # После тестов удаляем тренера
    db_session.delete(test_client)
    db_session.commit()
    db_session.close()


