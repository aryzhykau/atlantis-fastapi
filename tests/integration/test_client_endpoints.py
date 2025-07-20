import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_db
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

def test_create_client_endpoint(db_session):
    # Arrange
    client_data = {
        "first_name": "Test",
        "last_name": "Client",
        "email": "test.client@example.com",
        "phone": "1234567890",
        "date_of_birth": "2000-01-01",
        "is_student": True,
        "students": [
            {
                "first_name": "Test",
                "last_name": "Student",
                "date_of_birth": "2010-01-01"
            }
        ]
    }
    # TODO: Add authentication headers
    # Act
    response = client.post("/clients/", json=client_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test.client@example.com"
