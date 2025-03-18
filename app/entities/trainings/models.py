from sqlalchemy import Column, Integer, ForeignKey, Date, Time, DateTime
from app.database import Base


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_date = Column(Date, nullable=False)
    training_time = Column(Time, nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
