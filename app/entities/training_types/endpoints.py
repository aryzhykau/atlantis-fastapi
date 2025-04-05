from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.entities.training_types.crud import create_training_type, get_training_types, get_training_type_by_id
from app.entities.training_types.schemas import TrainingTypeCreate, TrainingTypeRead
from app.entities.users.models import UserRoleEnum

router = APIRouter()

@router.post("/", response_model=TrainingTypeRead, status_code=201)
async def add_training_type(training_type: TrainingTypeCreate, db: Session = Depends(get_db), current_user = Depends(verify_jwt_token)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        return create_training_type(db, training_type)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/{training_type_id}", response_model=TrainingTypeRead)
async def read_training_type(training_type_id: int, db: Session = Depends(get_db)):
    training_type = get_training_type_by_id(db, training_type_id)
    if training_type is None:
        return {"message": "Training type not found"}
    return training_type


@router.get("/", response_model=list[TrainingTypeRead], )
async def read_training_types(db: Session = Depends(get_db), current_user = Depends(verify_jwt_token)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        training_types = get_training_types(db)
        return training_types
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

