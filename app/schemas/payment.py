from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from app.models.payment_history import OperationType


class PaymentBase(BaseModel):
    """Базовая схема платежа"""
    amount: float = Field(..., description="Сумма платежа")
    description: Optional[str] = Field(None, description="Описание платежа")


class PaymentCreate(PaymentBase):
    """Схема для создания платежа"""
    client_id: int = Field(..., description="ID клиента")

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('description')
    def description_must_be_less_than_500_characters(cls, v):
        if len(v) > 500:
            raise ValueError('Description must be less than 500 characters')
        return v

class PaymentUpdate(BaseModel):
    """Схема для обновления платежа"""
    amount: Optional[float] = Field(None, description="Сумма платежа")
    description: Optional[str] = Field(None, description="Описание платежа")


class PaymentUpdate(BaseModel):
    """Схема для обновления платежа"""
    amount: Optional[float] = Field(None, description="Сумма платежа")
    description: Optional[str] = Field(None, description="Описание платежа")


class PaymentResponse(PaymentBase):
    """Схема ответа с информацией о платеже"""
    id: int
    client_id: int
    payment_date: datetime
    registered_by_id: int
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None

    model_config = {"from_attributes": True}


class PaymentExtendedResponse(PaymentBase):
    """Расширенная схема ответа с информацией о платеже и связанных объектах"""
    id: int
    client_id: int
    payment_date: datetime
    registered_by_id: int
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None
    
    # Связанные данные
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    registered_by_first_name: Optional[str] = None
    registered_by_last_name: Optional[str] = None

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


# Новые схемы для страницы лога транзакций
class PaymentHistoryFilterRequest(BaseModel):
    """Схема для фильтрации истории платежей"""
    operation_type: Optional[str] = Field(None, description="Тип операции")
    client_id: Optional[int] = Field(None, description="ID клиента")
    created_by_id: Optional[int] = Field(None, description="ID создателя операции")
    date_from: Optional[str] = Field(None, description="Дата начала периода (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="Дата окончания периода (YYYY-MM-DD)")
    amount_min: Optional[float] = Field(None, description="Минимальная сумма")
    amount_max: Optional[float] = Field(None, description="Максимальная сумма")
    description_search: Optional[str] = Field(None, description="Поиск по описанию")
    skip: int = Field(0, description="Количество записей для пропуска")
    limit: int = Field(100, description="Максимальное количество записей")


class PaymentHistoryExtendedResponse(BaseModel):
    """Расширенная схема ответа с информацией о связанных объектах"""
    id: int
    client_id: int
    payment_id: Optional[int] = None
    invoice_id: Optional[int] = None
    operation_type: OperationType
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str] = None
    created_at: datetime
    created_by_id: int
    
    # Связанные данные
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    created_by_first_name: Optional[str] = None
    created_by_last_name: Optional[str] = None
    payment_description: Optional[str] = None

    model_config = {"from_attributes": True}


class PaymentHistoryListResponse(BaseModel):
    """Схема ответа со списком истории платежей и пагинацией"""
    items: List[PaymentHistoryExtendedResponse]
    total: int
    skip: int
    limit: int
    has_more: bool

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    """Схема ответа со списком платежей и пагинацией"""
    payments: List[PaymentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool

    model_config = {"from_attributes": True} 