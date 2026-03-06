"""Pydantic схемы для системы абонементов v2."""
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Subscription template
# ---------------------------------------------------------------------------

class SubscriptionResponseV2(BaseModel):
    """Шаблон абонемента с полем sessions_per_week (v2)."""
    id: int
    name: str
    price: float
    sessions_per_week: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# StudentSubscription
# ---------------------------------------------------------------------------

class StudentSubscriptionCreateV2(BaseModel):
    """Создание абонемента студенту (v2).

    start_date вычисляется сервером (= текущая дата покупки).
    """
    student_id: int = Field(..., description="ID студента")
    subscription_id: int = Field(..., description="ID шаблона абонемента")
    is_auto_renew: bool = Field(False, description="Включить автопродление")


class StudentSubscriptionResponseV2(BaseModel):
    """Ответ с данными абонемента студента (v2)."""
    id: int
    student_id: int
    subscription_id: int
    start_date: datetime
    end_date: datetime
    is_auto_renew: bool
    status: str

    # v2 поля
    payment_due_date: Optional[date] = None
    is_prorated: bool = False
    sessions_per_week: Optional[int] = None

    # Legacy поля (оставлены для backward compat фронта)
    sessions_left: Optional[int] = None

    model_config = {"from_attributes": True}


class StudentSubscriptionListV2(BaseModel):
    items: List[StudentSubscriptionResponseV2]
    total: int


# ---------------------------------------------------------------------------
# MissedSession
# ---------------------------------------------------------------------------

class MissedSessionResponse(BaseModel):
    id: int
    student_id: int
    student_subscription_id: int
    real_training_student_id: int
    is_excused: bool
    excused_by_id: Optional[int] = None
    excused_at: Optional[datetime] = None
    makeup_deadline_date: Optional[date] = None
    made_up_at: Optional[datetime] = None
    made_up_real_training_student_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MissedSessionList(BaseModel):
    items: List[MissedSessionResponse]
    total: int


# ---------------------------------------------------------------------------
# SystemSettings
# ---------------------------------------------------------------------------

class SystemSettingResponse(BaseModel):
    key: str
    value: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    key: str = Field(..., description="Ключ настройки")
    value: str = Field(..., description="Новое значение")
