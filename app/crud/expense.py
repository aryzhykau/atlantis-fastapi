from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.expense import Expense, ExpenseType
from app.schemas.expense import ExpenseCreate, ExpenseTypeCreate, ExpenseUpdate
from datetime import datetime

def create_expense(db: Session, expense: ExpenseCreate) -> Expense:
    db_expense = Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def get_expense(db: Session, expense_id: int) -> Optional[Expense]:
    return db.query(Expense).filter(Expense.id == expense_id).first()

def get_expenses(db: Session, user_id: Optional[int] = None, expense_type_id: Optional[int] = None, start_date: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Expense]:
    query = db.query(Expense)
    if user_id:
        query = query.filter(Expense.user_id == user_id)
    if expense_type_id:
        query = query.filter(Expense.expense_type_id == expense_type_id)
    if start_date:
        query = query.filter(Expense.expense_date >= datetime.fromisoformat(start_date.replace('Z', '')))
    return query.offset(skip).limit(limit).all()

def update_expense(db: Session, expense_id: int, expense: ExpenseUpdate) -> Optional[Expense]:
    db_expense = get_expense(db, expense_id)
    if db_expense:
        update_data = expense.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_expense, key, value)
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
    return db_expense

def delete_expense(db: Session, expense_id: int) -> Optional[Expense]:
    db_expense = get_expense(db, expense_id)
    if db_expense:
        db.delete(db_expense)
        db.commit()
    return db_expense

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