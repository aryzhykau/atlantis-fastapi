from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional


# Обобщенная схема для TrainingType
class TrainingTypeBase(BaseModel):
    id: int
    name: str
    is_subscription_only: bool
    price: Optional[float] = None
    color: str

    model_config = {"from_attributes": True}


# Схема для создания нового типа тренировки
class TrainingTypeCreate(BaseModel):
    name: str = Field(...)
    is_subscription_only: bool = Field(...)
    price: Optional[float] = Field(None)
    color: Optional[str] = Field(...)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Йога для начинающих",
                    "is_subscription_only": False,
                    "price": 15.99,
                    "color": "#FFFFFF",
                },
                {
                    "name": "Фитнес",
                    "is_subscription_only": True,
                    "price": None,
                    "color": "#000000",
                },
            ]
        }
    )

    @field_validator("price", mode="before")
    def validate_price(cls, value, info):
        is_subscription_only = info.data.get("is_subscription_only")
        if is_subscription_only is False and value is None:
            raise ValueError("Price is required if training is not subscription-only")
        if is_subscription_only is True and value is not None:
            raise ValueError("Price must be None if training is subscription-only")
        return value


# Схема для обновления существующего типа тренировки
class TrainingTypeUpdate(BaseModel):
    name: Optional[str] = Field(None)
    is_subscription_only: Optional[bool] = Field(None)
    price: Optional[float] = Field(None)
    color: Optional[str] = Field(None)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Пилатес",
                    "is_subscription_only": True,
                    "price": 19.99,
                    "color": "#000000",
                },
                {
                    "name": "Кроссфит",
                    "is_subscription_only": False,
                    "price": 25.00,
                    "color": "#FF5733",
                },
            ]
        }
    )


# Схема для ответа на запросы типа тренировки
class TrainingTypeResponse(TrainingTypeBase):
    pass


# Схема для списка типов тренировок
class TrainingTypesList(BaseModel):
    training_types: list[TrainingTypeResponse]