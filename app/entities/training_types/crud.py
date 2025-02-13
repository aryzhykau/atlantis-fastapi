# from sqlalchemy.orm import Session
# from app.entities.training_types.models import TrainingType
# from app.entities.training_types.schemas import TrainingTypeCreate
#
# def create_training_type(db: Session, training_type: TrainingTypeCreate):
#     db_training_type = TrainingType(**training_type.dict())
#     db.add(db_training_type)
#     db.commit()
#     db.refresh(db_training_type)
#     return db_training_type
#
# def get_training_type_by_id(db: Session, training_type_id: int):
#     return db.query(TrainingType).filter(TrainingType.id == training_type_id).first()
#
# def get_training_types(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(TrainingType).offset(skip).limit(limit).all()
