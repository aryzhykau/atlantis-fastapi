# from pydantic import BaseModel
# from typing import Optional
# from datetime import date
# import enum
#
# class PaymentTypeEnum(str, enum.Enum):
#     trial = "Пробное занятие"
#     individual = "Индивидуальная тренировка"
#     pair = "Парная тренировка"
#     subscription_4 = "Абонемент на 4 занятия"
#     subscription_8 = "Абонемент на 8 занятий"
#     subscription_extend = "Продление абонемента"
#
# class PaymentCreate(BaseModel):
#     amount: float
#     payment_type: PaymentTypeEnum
#     date: date
#     client_id: int
#     coach_id: int
#
#     class Config:
#         orm_mode = True
#
# class SubscriptionCreate(BaseModel):
#     start_date: date
#     end_date: date
#     remaining_sessions: int
#     client_id: int
#     subscription_type: PaymentTypeEnum
#
#     class Config:
#         orm_mode = True
