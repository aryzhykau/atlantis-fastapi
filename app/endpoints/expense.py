from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.expense import Expense, ExpenseCreate, ExpenseUpdate, ExpenseType, ExpenseTypeCreate
from app.services.financial import FinancialService
from app.auth.permissions import get_current_user

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Expense)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["TRAINER", "ADMIN", "OWNER"]))):
    financial_service = FinancialService(db)
    return financial_service.create_expense(expense_data=expense)

@router.get("/", response_model=List[Expense])
def read_expenses(user_id: int = None, expense_type_id: int = None, start_date: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    expenses = financial_service.get_expenses(user_id=user_id, expense_type_id=expense_type_id, start_date=start_date, skip=skip, limit=limit)
    return expenses

@router.put("/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, expense: ExpenseUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["TRAINER", "ADMIN", "OWNER"]))):
    financial_service = FinancialService(db)
    db_expense = financial_service.update_expense(expense_id, expense)
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return db_expense

@router.delete("/{expense_id}", response_model=Expense)
def delete_expense(expense_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["TRAINER", "ADMIN", "OWNER"]))):
    financial_service = FinancialService(db)
    db_expense = financial_service.delete_expense(expense_id)
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return db_expense

@router.post("/types/", response_model=ExpenseType)
def create_expense_type(expense_type: ExpenseTypeCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["OWNER"]))):
    financial_service = FinancialService(db)
    return financial_service.create_expense_type(expense_type_data=expense_type)

@router.put("/types/{expense_type_id}", response_model=ExpenseType)
def update_expense_type(expense_type_id: int, expense_type: ExpenseTypeCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["OWNER"]))):
    financial_service = FinancialService(db)
    db_expense_type = financial_service.update_expense_type(expense_type_id, expense_type)
    if db_expense_type is None:
        raise HTTPException(status_code=404, detail="Expense type not found")
    return db_expense_type

@router.delete("/types/{expense_type_id}", response_model=ExpenseType)
def delete_expense_type(expense_type_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user(["OWNER"]))):
    financial_service = FinancialService(db)
    db_expense_type = financial_service.delete_expense_type(expense_type_id)
    if db_expense_type is None:
        raise HTTPException(status_code=404, detail="Expense type not found")
    return db_expense_type

@router.get("/types/", response_model=List[ExpenseType])
def read_expense_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    expense_types = financial_service.get_expense_types(skip=skip, limit=limit)
    return expense_types 