from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.endpoints.users import get_current_user
from app.entities.payments.crud import create_payment, get_payments
from app.entities.payments.schemas import PaymentCreate, PaymentRead
from app.entities.users.models import UserRoleEnum

router = APIRouter()

@router.post("/", response_model=PaymentRead)
async def make_payment(payment_data: PaymentCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    new_payment = create_payment(db, payment_data)
    return PaymentRead.model_validate(new_payment)

@router.get("/", response_model=list[PaymentRead])
async def get_all_payments(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    payments = get_payments(db)
    return [PaymentRead.model_validate(payment) for payment in payments]


