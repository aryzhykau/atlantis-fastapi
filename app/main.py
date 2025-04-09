import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.auth import router as auth_router
from app.endpoints.clients import router as clients_router
from app.endpoints.trainers import router as trainers_router
from app.endpoints.users import router as users_router
from app.entities.subscriptions.endpoints import subscriptions_router
from app.entities.training_types.endpoints import router as training_types_router
# from app.endpoints.admins import router as admins_router
from app.entities.trainings.endpoints import router as trainings_router

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sqlalchemy").setLevel(logging.DEBUG)
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
app.include_router(trainings_router, prefix="/trainings", tags=["trainings"])
app.include_router(training_types_router, prefix="/training_types", tags=["training_types"])
app.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
# app.include_router(admins_router, prefix="/admin", tags=["admins"])
