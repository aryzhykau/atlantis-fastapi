import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_db
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserRole
from app.auth.jwt_handler import create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_read_users_me(db_session):
    # Arrange
    user = User(email="test@example.com", first_name="Test", last_name="User", role=UserRole.CLIENT, phone="1234567890", date_of_birth=date(2000, 1, 1), is_authenticated_with_google=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Act
    response = client.get("/users/me", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["id"] == user.id
