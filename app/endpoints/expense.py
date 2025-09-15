from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.expense import Expense, ExpenseCreate, ExpenseType, ExpenseTypeCreate
from app.services.financial import FinancialService

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Expense)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    return financial_service.create_expense(expense_data=expense)

@router.get("/", response_model=List[Expense])
def read_expenses(user_id: int = None, expense_type_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    expenses = financial_service.get_expenses(user_id=user_id, expense_type_id=expense_type_id, skip=skip, limit=limit)
    return expenses

@router.post("/types/", response_model=ExpenseType)
def create_expense_type(expense_type: ExpenseTypeCreate, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    return financial_service.create_expense_type(expense_type_data=expense_type)

@router.get("/types/", response_model=List[ExpenseType])
def read_expense_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    financial_service = FinancialService(db)
    expense_types = financial_service.get_expense_types(skip=skip, limit=limit)
    return expense_types 