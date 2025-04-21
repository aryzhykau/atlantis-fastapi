from sqlalchemy import Boolean, Column, Float, Integer, String
from app.database import Base


class TrainingType(Base):
    __tablename__ = "training_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_subscription_only = Column(Boolean, default=False)
    price = Column(Float, nullable=True)
    color = Column(String, nullable=False)

    def __repr__(self):
        return f"<TrainingType(id={self.id}, name={self.name}, subscription_only={self.is_subscription_only})>"