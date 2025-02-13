# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.dependencies import get_db
# from app.crud.payment import create_payment, create_subscription, extend_subscription
# from app.models.payment import PaymentTypeEnum
#
# router = APIRouter()
#
# @router.post("/payments/")
# async def make_payment(client_id: int, amount: float, payment_type: PaymentTypeEnum, db: Session = Depends(get_db)):
#     payment = create_payment(db, client_id, amount, payment_type)
#     return payment
#
# @router.post("/subscriptions/")
# async def create_new_subscription(client_id: int, subscription_type: PaymentTypeEnum, start_date: date, remaining_sessions: int, db: Session = Depends(get_db)):
#     subscription = create_subscription(db, client_id, subscription_type, start_date, remaining_sessions)
#     return subscription
#
# @router.post("/subscriptions/extend/{client_id}")
# async def extend_subscription_for_client(client_id: int, additional_sessions: int, db: Session = Depends(get_db)):
#     subscription = extend_subscription(db, client_id, additional_sessions)
#     if subscription is None:
#         raise HTTPException(status_code=404, detail="No active subscription found")
#     return subscription
