import logging

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.auth import router as auth_router
from app.endpoints import (
    client,
    student,
    trainer,
    subscription,
    real_trainings,
    training_type,
    payment,
    invoice,
    cron,
    health,
    expense,
    training_template,
    training_student_template,
    user,
    trainer_salaries
)
from app.endpoints import client_contacts

logging.basicConfig(level=logging.DEBUG) # Ensure basic config is debug

# Create a logger for the application
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler and set its level to DEBUG
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

logger.info("Application started and logger configured.") # Test log message



app = FastAPI(
    title="Atlantis API",
    description="API для управления тренировками и финансами",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


# Регистрация маршрутов
app.include_router(auth_router)
app.include_router(user.router)
app.include_router(health.router)
app.include_router(client.router)
app.include_router(student.router)
app.include_router(trainer.router)
app.include_router(subscription.router)
app.include_router(real_trainings.router)
app.include_router(training_type.router)
app.include_router(payment.router)
app.include_router(invoice.router)
app.include_router(cron.router)
app.include_router(expense.router)
app.include_router(training_template.router)
app.include_router(training_student_template.router)
app.include_router(trainer_salaries.router)
app.include_router(client_contacts.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to User Management API"}


@app.get("/healthz")
async def healthz():
    return {"message": "Healthy!"}


# Обработка ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        if 'ctx' in error and 'error' in error['ctx']:
            # Если ошибка содержит ValueError, берем его сообщение
            if isinstance(error['ctx']['error'], ValueError):
                error['msg'] = str(error['ctx']['error'])
                del error['ctx']  # Удаляем ctx, так как он содержит несериализуемые объекты
        errors.append(error)
    
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


# Проверка подключения к базе данных
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Проверяем подключение к базе данных
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": "disconnected"}
