from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.expense import Expense, ExpenseType
from app.schemas.expense import ExpenseCreate, ExpenseTypeCreate

def create_expense(db: Session, expense: ExpenseCreate) -> Expense:
    db_expense = Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def get_expenses(db: Session, user_id: Optional[int] = None, expense_type_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Expense]:
    query = db.query(Expense)
    if user_id:
        query = query.filter(Expense.user_id == user_id)
    if expense_type_id:
        query = query.filter(Expense.expense_type_id == expense_type_id)
    return query.offset(skip).limit(limit).all()

def create_expense_type(db: Session, expense_type: ExpenseTypeCreate) -> ExpenseType:
    db_expense_type = ExpenseType(**expense_type.dict())
    db.add(db_expense_type)
    db.commit()
    db.refresh(db_expense_type)
    return db_expense_type

def get_expense_types(db: Session, skip: int = 0, limit: int = 100) -> List[ExpenseType]:
    return db.query(ExpenseType).offset(skip).limit(limit).all()

def get_expense_type_by_name(db: Session, name: str) -> Optional[ExpenseType]:
    return db.query(ExpenseType).filter(ExpenseType.name == name).first() 