import datetime
import logging

from sqlalchemy.orm import Session

from app.entities.training_types.models import TrainingType
from app.entities.training_types.schemas import TrainingTypeCreate, TrainingTypeRead

logger = logging.getLogger(__name__)


def create_training_type(db: Session, training_type: TrainingTypeCreate):
    try:
        new_training_type = training_type.model_dump()
        new_training_type["created_at"] = new_training_type["updated_at"] = datetime.datetime.now()
        db_training_type = TrainingType(**new_training_type)
        db.add(db_training_type)
        db.commit()
        db.refresh(db_training_type)
        return db_training_type
    except Exception as e:
        db.rollback()
        raise e


def update_training_type(db: Session, training_type_id: int, updates: TrainingTypeCreate):
    db_training_type = db.query(TrainingType).filter(TrainingType.id == training_type_id).first()
    if not db_training_type:
        raise ValueError("Training type not found")
    try:
        for key, value in updates.model_dump().items():
            setattr(db_training_type, key, value)
        db_training_type.updated_at = datetime.datetime.now()
        db.commit()
        db.refresh(db_training_type)
        return TrainingTypeRead.model_validate(db_training_type)
    except Exception as e:
        db.rollback()
        raise e


def delete_training_type(db: Session, training_type_id: int):
    db_training_type = db.query(TrainingType).filter(TrainingType.id == training_type_id).first()
    if not db_training_type:
        raise ValueError("Training type not found")
    try:
        db.delete(db_training_type)
        db.commit()
        return {"message": "Training type successfully deleted"}
    except Exception as e:
        db.rollback()
        raise e


def get_training_type_by_id(db: Session, training_type_id: int):
    training_type = db.query(TrainingType).get(training_type_id)
    if not training_type:
        raise ValueError(f"Тип тренировки с ID {training_type_id} не существует.")
    return training_type


def get_training_types(db: Session):
    training_types = db.query(TrainingType).order_by(TrainingType.title).all()
    logger.debug(f"TRAINING TYPES = {training_types}")
    return [TrainingTypeRead.model_validate(training_type) for training_type in training_types] if training_types else []


