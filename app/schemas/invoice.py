from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models import InvoiceType, InvoiceStatus


class UserBasic(BaseModel):
    """Basic user information for invoice responses"""
    id: int
    first_name: str
    last_name: str
    
    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    """Базовая схема инвойса"""
    client_id: int = Field(..., description="ID клиента")
    student_id: Optional[int] = Field(None, description="ID студента")
    amount: float = Field(..., description="Сумма")
    description: str = Field(..., description="Описание/причина")
    is_auto_renewal: bool = Field(False, description="Создан ли для автопродления")


class InvoiceCreate(InvoiceBase):
    """Общая схема для создания инвойса"""
    subscription_id: Optional[int] = Field(None, description="ID абонемента")
    training_id: Optional[int] = Field(None, description="ID тренировки")
    type: InvoiceType = Field(..., description="Тип инвойса")
    status: InvoiceStatus = Field(InvoiceStatus.UNPAID, description="Статус инвойса")
    student_subscription_id: Optional[int] = Field(None, description="ID подписки студента")


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
    
    # Include client information
    client: Optional[UserBasic] = None

    model_config = {"from_attributes": True}


class InvoiceUpdate(BaseModel):
    """Схема для обновления инвойса"""
    amount: Optional[float] = Field(None, description="Сумма")
    description: Optional[str] = Field(None, description="Описание/причина")
    status: Optional[InvoiceStatus] = Field(None, description="Статус инвойса")
    paid_at: Optional[datetime] = Field(None, description="Дата оплаты")
    cancelled_at: Optional[datetime] = Field(None, description="Дата отмены")
    cancelled_by_id: Optional[int] = Field(None, description="ID пользователя, отменившего инвойс")


class InvoiceList(BaseModel):
    """Схема списка инвойсов"""
    items: List[InvoiceResponse]
    total: int 