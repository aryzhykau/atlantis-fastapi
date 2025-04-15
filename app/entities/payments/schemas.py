from datetime import datetime

from pydantic import BaseModel


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
class PaymentCreate(BaseModel):
    amount: float
    payment_date: datetime
    user_id: int



class PaymentRead(BaseModel):
    id: int
    payment_date: datetime
    user_id: int

    model_config = {"from_attributes": True}