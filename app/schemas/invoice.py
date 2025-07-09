from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models import InvoiceType, InvoiceStatus


class InvoiceBase(BaseModel):
    """Базовая схема инвойса"""
    client_id: int = Field(..., description="ID клиента")
    student_id: Optional[int] = Field(None, description="ID студента")
    amount: float = Field(..., description="Сумма")
    description: str = Field(..., description="Описание/причина")
    is_auto_renewal: bool = Field(False, description="Создан ли для автопродления")


class SubscriptionInvoiceCreate(InvoiceBase):
    """Схема для создания инвойса для абонемента"""
    subscription_id: int = Field(..., description="ID абонемента")


class TrainingInvoiceCreate(InvoiceBase):
    """Схема для создания инвойса для тренировки"""
    training_id: int = Field(..., description="ID тренировки")


class InvoiceResponse(BaseModel):
    """Схема ответа с информацией об инвойсе"""
    id: int
    client_id: int
    student_id: Optional[int]
    subscription_id: Optional[int]
    training_id: Optional[int]
    type: InvoiceType
    amount: float
    description: str
    status: InvoiceStatus
    created_at: datetime
    paid_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None
    is_auto_renewal: bool

    model_config = {"from_attributes": True}


class InvoiceList(BaseModel):
    """Схема списка инвойсов"""
    items: List[InvoiceResponse]
    total: int 