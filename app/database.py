from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://myuser:mypassword@localhost:5433/mydatabase"

# Создаем подключение к базе
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Создаем сессию для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей
Base = declarative_base()


from app.entities.users.models import *
from app.entities.training_types.models import *
from app.entities.trainings.models import *
from app.entities.subscriptions.models import *
from app.entities.invoices.models import *
from app.entities.payments.models import *
from app.entities.relations_models.client_subscriptions import *
from app.entities.relations_models.invoice_payments import *