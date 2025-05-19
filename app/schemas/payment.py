from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.payment_history import OperationType


class PaymentBase(BaseModel):
    """Базовая схема платежа"""
    amount: float = Field(..., description="Сумма платежа")
    description: str = Field(..., description="Описание платежа")


class PaymentCreate(PaymentBase):
    """Схема для создания платежа"""
    client_id: int = Field(..., description="ID клиента")


class PaymentResponse(PaymentBase):
    """Схема ответа с информацией о платеже"""
    id: int
    client_id: int
    payment_date: datetime
    registered_by_id: int
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None

    model_config = {"from_attributes": True}


class ClientBalanceResponse(BaseModel):
    """Схема ответа с балансом клиента"""
    client_id: int
    balance: float

    model_config = {"from_attributes": True}


class PaymentHistoryResponse(BaseModel):
    id: int
    client_id: int
    payment_id: int
    operation_type: OperationType
    amount: float
    balance_before: float
    balance_after: float
    description: str | None
    created_at: datetime
    created_by_id: int

    model_config = {"from_attributes": True} 