from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Expense(Base):
    """Модель расхода"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expense_type_id = Column(Integer, ForeignKey("expense_types.id"), nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    description = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="expenses")
    expense_type = relationship("ExpenseType", back_populates="expenses")

    def __repr__(self):
        return f"<Expense(id={self.id}, user_id={self.user_id}, amount={self.amount})>"


class ExpenseType(Base):
    """Модель типа расхода"""
    __tablename__ = "expense_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    # Relationships
    expenses = relationship("Expense", back_populates="expense_type")

    def __repr__(self):
        return f"<ExpenseType(id={self.id}, name={self.name})>" 