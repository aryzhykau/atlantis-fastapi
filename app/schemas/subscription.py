from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class SubscriptionBase(BaseModel):
    id: int
    name: str
    price: float
    number_of_sessions: int
    validity_days: int
    is_active: bool

    # Настройка, чтобы поддерживать работу с объектами моделей базы данных
    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(BaseModel):
    name: str = Field(...)
    price: float = Field(...)
    number_of_sessions: int = Field(...)
    validity_days: int = Field(...)
    is_active: Optional[bool] = Field(True)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Абонемент на йогу",
                    "price": 1500.00,
                    "number_of_sessions": 10,
                    "validity_days": 30,
                    "is_active": True,
                },
                {
                    "name": "Тренажёрный зал",
                    "price": 2000.00,
                    "number_of_sessions": 8,
                    "validity_days": 60,
                    "is_active": False,
                },
            ]
        }
    )

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(None)
    price: Optional[float] = Field(None)
    number_of_sessions: Optional[int] = Field(None)
    validity_days: Optional[int] = Field(None)
    is_active: Optional[bool] = Field(None)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Абонемент на пилатес",
                    "price": 1800.00,
                },
                {
                    "is_active": False,
                    "validity_days": 90,
                },
            ]
        }
    )

class SubscriptionResponse(SubscriptionBase):
    pass


class SubscriptionsList(BaseModel):
    subscriptions: list[SubscriptionResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "subscriptions": [
                        {
                            "id": 1,
                            "name": "Йога для начинающих",
                            "price": 1500.00,
                            "number_of_sessions": 10,
                            "validity_days": 30,
                            "is_active": True,
                        },
                        {
                            "id": 2,
                            "name": "Кроссфит",
                            "price": 2500.00,
                            "number_of_sessions": 15,
                            "validity_days": 60,
                            "is_active": True,
                        },
                    ]
                }
            ]
        }
    )