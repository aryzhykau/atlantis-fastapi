import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .schemas import TrainingWithClientsCreate, TrainingWithClientsRead
from .crud import create_training_with_clients
from app.dependencies import get_db


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TrainingWithClientsRead, status_code=201)
def create_training(
        training_data: TrainingWithClientsCreate,
        db: Session = Depends(get_db),
):
    """
    Создаёт тренировку с назначенными пользователями.
    """
    logger.debug("Training data",training_data)
    try:
        training = create_training_with_clients(db, training_data)
        return training
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
