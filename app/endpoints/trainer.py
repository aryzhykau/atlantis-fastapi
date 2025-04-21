from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import TrainerCreate, TrainerResponse, TrainerUpdate, TrainersList, UserRole
from app.crud.trainer import (create_trainer, get_trainer, get_all_trainers,
                              update_trainer, delete_trainer)

router = APIRouter(prefix="/trainers", tags=["Trainers"])


# Создание тренера
@router.post("/", response_model=TrainerResponse)
def create_trainer_endpoint(trainer_data: TrainerCreate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return create_trainer(db, trainer_data)


# Получение списка тренеров
@router.get("/", response_model=TrainersList)
def get_trainers_endpoint(current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return TrainersList(trainers=get_all_trainers(db))


# Получение тренера по ID
@router.get("/{trainer_id}", response_model=TrainerResponse)
def get_trainer_endpoint(trainer_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = get_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer


# Обновление тренера
@router.patch("/{trainer_id}", response_model=TrainerResponse)
def update_trainer_endpoint(trainer_id: int, trainer_data: TrainerUpdate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = update_trainer(db, trainer_id, trainer_data)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer


# Удаление тренера
@router.delete("/{trainer_id}", response_model=TrainerResponse)
def delete_trainer_endpoint(trainer_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    trainer = delete_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer