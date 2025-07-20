from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os

from app.config import config  # Создаем подключение к базе

engine = create_engine(config.SQLALCHEMY_DATABASE_URI)

# Создаем сессию для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей
Base = declarative_base()


from sqlalchemy.orm import Session

@contextmanager
def transactional(db: Session):
    """
    A context manager for handling database transactions that is aware of the testing environment.

    In production, it commits or rolls back the transaction.
    In testing, it only flushes the session, leaving the final commit/rollback
    to the test runner's transactional fixture.
    """
    # Check an environment variable to see if we're in a test environment.
    # We will set this in our test configuration.
    is_test_mode = os.getenv("TESTING", "false").lower() == "true"

    if not is_test_mode:
        # Production behavior: real transactions
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
    else:
        # Testing behavior: no commits, just flush
        # This makes the data available for reads within the same test,
        # but it will all be rolled back by the test fixture.
        try:
            yield db
            db.flush()
        except Exception:
            db.rollback() # Rollback to a clean state even within the test
            raise