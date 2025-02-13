# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from app.dependencies import get_db
# from app.entities.training_types.schemas import TrainingTypeCreate
# from app.entities.training_types.crud import create_training_type, get_training_types, get_training_type_by_id
#
# router = APIRouter()
#
# @router.post("/")
# async def add_training_type(training_type: TrainingTypeCreate, db: Session = Depends(get_db)):
#     return await create_training_type(db, training_type)
#
# @router.get("/{training_type_id}")
# async def read_training_type(training_type_id: int, db: Session = Depends(get_db)):
#     training_type = await get_training_type_by_id(db, training_type_id)
#     if training_type is None:
#         return {"message": "Training type not found"}
#     return training_type
#
# @router.get("/")
# async def read_training_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     training_types = await get_training_types(db, skip=skip, limit=limit)
#     return training_types
