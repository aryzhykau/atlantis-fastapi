import logging

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.auth import router as auth_router
from app.dependencies import get_db
from app.endpoints.user import router as user_router
from app.endpoints.client import router as client_router
from app.endpoints.trainer import router as trainer_router
from app.endpoints.training_type import router as training_type_router
from app.endpoints.subscription import router as subscription_router
from app.endpoints.student import router as student_router

logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("sqlalchemy").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


# Регистрация маршрутов
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(client_router)
app.include_router(trainer_router)
app.include_router(training_type_router)
app.include_router(subscription_router)
app.include_router(student_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to User Management API"}


@app.get("/healthz")
async def healthz():
    return {"message": "Healthy!"}
