from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class TrainingType(Base):
    __tablename__ = "training_types"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)  # Название типа тренировки
    require_subscription = Column(Boolean, default=False)  # Описание типа тренировки
