from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class SubscriptionBase(BaseModel):
    """Базовая схема абонемента"""
    name: str = Field(..., description="Название абонемента")
    price: float = Field(..., description="Стоимость абонемента")
    number_of_sessions: int = Field(..., description="Количество тренировок")
    validity_days: int = Field(..., description="Срок действия в днях")
    is_active: bool = Field(True, description="Активен ли абонемент")


class SubscriptionCreate(SubscriptionBase):
    """Схема для создания абонемента"""
    pass


class SubscriptionUpdate(BaseModel):
    """Схема для обновления абонемента"""
    name: Optional[str] = Field(None, description="Название абонемента")
    price: Optional[float] = Field(None, description="Стоимость абонемента")
    number_of_sessions: Optional[int] = Field(None, description="Количество тренировок")
    validity_days: Optional[int] = Field(None, description="Срок действия в днях")
    is_active: Optional[bool] = Field(None, description="Активен ли абонемент")


class SubscriptionResponse(SubscriptionBase):
    """Схема ответа с информацией об абонементе"""
    id: int

    model_config = {"from_attributes": True}


class StudentSubscriptionBase(BaseModel):
    """Базовая схема подписки студента"""
    student_id: int = Field(..., description="ID студента")
    subscription_id: int = Field(..., description="ID абонемента")
    is_auto_renew: bool = Field(False, description="Включено ли автопродление")


class StudentSubscriptionCreate(StudentSubscriptionBase):
    """Схема для создания подписки студента"""
    start_date: Optional[datetime] = Field(None, description="Дата начала подписки")
    end_date: Optional[datetime] = Field(None, description="Дата окончания подписки")
    sessions_left: Optional[int] = Field(None, description="Оставшиеся тренировки")
    transferred_sessions: Optional[int] = Field(0, description="Перенесенные тренировки")
    freeze_start_date: Optional[datetime] = Field(None, description="Начало периода заморозки")
    freeze_end_date: Optional[datetime] = Field(None, description="Конец периода заморозки")


class StudentSubscriptionUpdate(BaseModel):
    """Схема для обновления подписки студента"""
    end_date: Optional[datetime] = Field(None, description="Дата окончания подписки")
    freeze_start_date: Optional[datetime] = Field(None, description="Начало периода заморозки")
    freeze_end_date: Optional[datetime] = Field(None, description="Конец периода заморозки")
    is_auto_renew: Optional[bool] = Field(None, description="Включить/выключить автопродление")
    sessions_left: Optional[int] = Field(None, description="Оставшиеся тренировки")
    transferred_sessions: Optional[int] = Field(None, description="Перенесенные тренировки")


class StudentSubscriptionResponse(StudentSubscriptionBase):
    """Схема ответа с информацией о подписке студента"""
    id: int
    start_date: datetime
    end_date: datetime
    freeze_start_date: Optional[datetime] = None
    freeze_end_date: Optional[datetime] = None
    sessions_left: int
    transferred_sessions: int
    auto_renewal_invoice_id: Optional[int] = None
    status: str

    model_config = {"from_attributes": True}


class SubscriptionFreeze(BaseModel):
    """Схема для заморозки подписки"""
    freeze_start_date: datetime = Field(..., description="Дата начала заморозки")
    freeze_duration_days: int = Field(..., description="Длительность заморозки в днях")


class SubscriptionList(BaseModel):
    """Схема списка абонементов"""
    items: List[SubscriptionResponse]
    total: int