from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ExpenseBase(BaseModel):
    amount: float
    description: Optional[str] = None
    expense_date: datetime
    expense_type_id: int
    user_id: int

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int

    class Config:
        orm_mode = True

class ExpenseTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class ExpenseTypeCreate(ExpenseTypeBase):
    pass

class ExpenseType(ExpenseTypeBase):
    id: int

    class Config:
        orm_mode = True 