import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from .crud import create_training_with_clients, get_all_trainings
from .schemas import TrainingWithClientsCreate, TrainingWithClientsRead
from ..users.models import UserRoleEnum

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[TrainingWithClientsRead], status_code=200)
def get_trainings(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    """
    Возвращает список тренировок текущего пользователя (тренера или клиента).
    """
    logger.debug(f"Fetching trainings for user {current_user['id']} with role {current_user['role']}.")


    if current_user["role"] == UserRoleEnum.ADMIN:
        trainings = get_all_trainings(db)

    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    return trainings


@router.post("/", response_model=TrainingWithClientsRead, status_code=201)
def create_training(
        training_data: TrainingWithClientsCreate,
        current_user = Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    """
    Создаёт тренировку с назначенными пользователями.
    """
    logger.debug("Training data",training_data)
    try:
        if current_user["role"] != UserRoleEnum.ADMIN:
            raise HTTPException(status_code=403, detail="Forbidden")
        else:
            training = create_training_with_clients(db, training_data)
            return training
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


