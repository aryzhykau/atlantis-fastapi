import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from .crud import create_training_with_clients, get_all_trainings
from .errors import TrainingError
from .schemas import TrainingWithClientsCreate, TrainingWithClientsRead
from ..users.models import UserRoleEnum

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[TrainingWithClientsRead], status_code=200)
def get_trainings(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
        trainer_id: int = None,
        start_week: datetime = None,
        end_week: datetime = None,
):
    """
    Возвращает список тренировок текущего пользователя (тренера или клиента).
    """



    if current_user["role"] == UserRoleEnum.ADMIN:
        trainings = get_all_trainings(db, trainer_id=trainer_id, start_week=start_week, end_week=end_week)

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

    try:
        if current_user["role"] != UserRoleEnum.ADMIN:
            raise HTTPException(status_code=403, detail="Forbidden")
        else:
            logger.debug("Creating training")
            training = create_training_with_clients(db, training_data)
            return TrainingWithClientsRead.model_validate(training)
    except TrainingError as e:
        raise HTTPException(status_code=400, detail=e.message)


