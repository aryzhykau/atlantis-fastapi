from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.endpoints.users import router as users_router
from app.endpoints.clients import router as clients_router
from app.endpoints.trainers import router as trainers_router
# from app.endpoints.admins import router as admins_router
from app.database import Base, engine
from app.auth.auth import router as auth_router
import logging


logging.basicConfig(level=logging.DEBUG)
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
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(clients_router, prefix="/clients", tags=["clients"])
app.include_router(trainers_router, prefix="/trainers", tags=["trainers"])
# app.include_router(admins_router, prefix="/admin", tags=["admins"])
