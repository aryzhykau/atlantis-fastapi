# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.dependencies import get_db
# from app.entities.users.models import User
# from app.entities.users.schemas import TrainerCreate, TrainerRead
# from typing import List
#
# router = APIRouter()
#
#
# @router.get("/trainers", response_model=List[TrainerRead])
# def get_trainers(db: Session = Depends(get_db)):
#     return db.query(Trainer).all()
#
#
# @router.get("/trainers/{trainer_id}", response_model=TrainerRead)
# def get_trainer(trainer_id: int, db: Session = Depends(get_db)):
#     trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
#     if not trainer:
#         raise HTTPException(status_code=404, detail="Тренер не найден")
#     return trainer
#
#
# @router.post("/trainers", response_model=TrainerRead)
# def create_trainer(trainer_data: TrainerCreate, db: Session = Depends(get_db)):
#     trainer = Trainer(**trainer_data.dict())
#     db.add(trainer)
#     db.commit()
#     db.refresh(trainer)
#     return trainer
#
#
# @router.delete("/trainers/{trainer_id}")
# def delete_trainer(trainer_id: int, db: Session = Depends(get_db)):
#     trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
#     if not trainer:
#         raise HTTPException(status_code=404, detail="Тренер не найден")
#
#     db.delete(trainer)
#     db.commit()
#     return {"message": "Тренер удалён"}
