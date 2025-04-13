from sqlalchemy import Column, Integer, String, Boolean, func, DateTime

from app.database import Base


class TrainingType(Base):
    __tablename__ = "training_types"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)  # Название типа тренировки
    require_subscription = Column(Boolean, default=False)  # Описание типа тренировки
    color = Column(String, nullable=False, server_default="#FFFFFF")
    price = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



