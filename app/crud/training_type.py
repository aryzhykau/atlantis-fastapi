from sqlalchemy.orm import Session
from app.models.training_type import TrainingType
from app.schemas.training_type import TrainingTypeCreate, TrainingTypeUpdate


def create_training_type(db: Session, training_type: TrainingTypeCreate) -> TrainingType:
    """Создает новый тип тренировки."""
    print("added")
    db_training_type = TrainingType(**training_type.model_dump())
    db.add(db_training_type)
    print("added")
    db.commit()
    db.refresh(db_training_type)
    return db_training_type


def get_training_type(db: Session, training_type_id: int) -> TrainingType | None:
    """Получает тип тренировки по ID."""
    return db.query(TrainingType).filter(TrainingType.id == training_type_id).first()


def get_training_types(db: Session, skip: int = 0, limit: int = 10) -> list[TrainingType]:
    """Получает список всех типов тренировок с пагинацией."""
    return db.query(TrainingType).order_by(TrainingType.name).offset(skip).limit(limit).all()


def update_training_type(
        db: Session, training_type_id: int, training_type_update: TrainingTypeUpdate
) -> TrainingType | None:
    """Обновляет существующий тип тренировки."""
    db_training_type = db.query(TrainingType).filter(TrainingType.id == training_type_id).first()
    if not db_training_type:
        return None

    update_data = training_type_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_training_type, key, value)

    db.commit()
    db.refresh(db_training_type)
    return db_training_type


def delete_training_type(db: Session, training_type_id: int) -> TrainingType | None:
    """Удаляет тип тренировки по ID."""
    db_training_type = db.query(TrainingType).filter(TrainingType.id == training_type_id).first()
    if not db_training_type:
        return None

    db.delete(db_training_type)
    db.commit()
    return db_training_type