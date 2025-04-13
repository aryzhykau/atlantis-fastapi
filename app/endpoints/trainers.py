import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.entities.users.crud import create_user, get_all_users_by_role, get_user_by_id
from app.entities.users.models import User, UserRoleEnum
from app.entities.users.schemas import TrainerCreate, TrainerRead

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/", response_model=List[TrainerRead])
def get_trainers(current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db),
                 page: int = Query(1, ge=1),
                 page_size: int = Query(10, ge=1, le=100)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug("Authorised for clients request")
    return get_all_users_by_role(db, UserRoleEnum.TRAINER)

@router.get("/{trainer_id}", response_model=TrainerRead)
def get_trainers(trainer_id, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug("Authorised for clients request")
        return get_user_by_id(db, UserRoleEnum.TRAINER, trainer_id)
    else:
        raise HTTPException(403, "Forbidden")



@router.delete("/{trainer_id}")
def delete_trainer(trainer_id: int, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления тренера")
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRoleEnum.TRAINER).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    db.delete(trainer)
    db.commit()
    return {"message": "Тренер успешно удален"}


#
# @router.get("/trainers/{trainer_id}", response_model=TrainerRead)
# def get_trainer(trainer_id: int, db: Session = Depends(get_db)):
#     trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
#     if not trainer:
#         raise HTTPException(status_code=404, detail="Тренер не найден")
#     return trainer
#
#

@router.put("/{trainer_id}", response_model=TrainerRead)
def update_trainer(trainer_id: int, trainer_data: TrainerCreate, current_user: dict = Depends(verify_jwt_token),
                   db: Session = Depends(get_db)):
    if current_user["role"] != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав для обновления тренера")
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRoleEnum.TRAINER).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Тренер не найден")
    for key, value in trainer_data.dict(exclude_unset=True).items():
        setattr(trainer, key, value)
    db.commit()
    db.refresh(trainer)
    return trainer


@router.post("/", response_model=TrainerRead)
def create_trainer(trainer_data: TrainerCreate, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        trainer_data.role = UserRoleEnum.TRAINER
        new_trainer = create_user(db, trainer_data)
        return new_trainer


