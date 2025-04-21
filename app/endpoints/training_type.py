import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.training_type import (
    TrainingTypeCreate,
    TrainingTypeUpdate,
    TrainingTypeResponse,
    TrainingTypesList,
)
from app.crud.training_type import (
    create_training_type,
    get_training_type,
    get_training_types,
    update_training_type,
    delete_training_type,
)
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training_types", tags=["Training Types"])


# Создание типа тренировки
@router.post("/", response_model=TrainingTypeResponse)
def create_training_type_endpoint(
        training_type_data: TrainingTypeCreate,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    logger.debug(training_type_data)
    print(training_type_data)
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    print("adding")
    new_training_type = create_training_type(db, training_type_data)
    return new_training_type


# Получение списка типов тренировок
@router.get("/", response_model=TrainingTypesList)
def get_training_types_endpoint(
        skip: int = 0,
        limit: int = 10,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Здесь доступ разрешен всем авторизованным пользователям
    training_types = get_training_types(db, skip=skip, limit=limit)
    return TrainingTypesList(training_types=training_types)


# Получение типа тренировки по ID
@router.get("/{training_type_id}", response_model=TrainingTypeResponse)
def get_training_type_endpoint(
        training_type_id: int,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Доступ разрешен всем авторизованным пользователям
    training_type = get_training_type(db, training_type_id)
    if not training_type:
        raise HTTPException(status_code=404, detail="Training type not found")
    return training_type


# Обновление типа тренировки
@router.patch("/{training_type_id}", response_model=TrainingTypeResponse)
def update_training_type_endpoint(
        training_type_id: int,
        training_type_data: TrainingTypeUpdate,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    updated_training_type = update_training_type(db, training_type_id, training_type_data)
    if not updated_training_type:
        raise HTTPException(status_code=404, detail="Training type not found")
    return updated_training_type


