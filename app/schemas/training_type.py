from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional


# Обобщенная схема для TrainingType
class TrainingTypeBase(BaseModel):
    id: int
    name: str
    is_subscription_only: bool
    price: Optional[float] = None
    color: str
    is_active: bool

    model_config = {"from_attributes": True}


# Схема для создания нового типа тренировки
class TrainingTypeCreate(BaseModel):
    name: str = Field(
        ..., 
        min_length=2, 
        max_length=50, 
        description="Название типа тренировки (от 2 до 50 символов)",
        error_messages={
            "min_length": "Название тренировки должно содержать минимум 2 символа",
            "max_length": "Название тренировки не должно превышать 50 символов",
            "type": "Название тренировки должно быть строкой"
        }
    )
    is_subscription_only: bool = Field(
        ...,
        description="Флаг, указывающий, доступна ли тренировка только по подписке",
        error_messages={
            "type": "Поле is_subscription_only должно быть булевым значением (true/false)"
        }
    )
    price: Optional[float] = Field(
        None, 
        ge=0, 
        description="Цена тренировки (должна быть больше или равна 0)",
        error_messages={
            "ge": "Цена не может быть отрицательной",
            "type": "Цена должна быть числом"
        }
    )
    color: str = Field(
        ..., 
        pattern="^#[0-9A-Fa-f]{6}$", 
        description="Цвет в формате HEX (#RRGGBB)",
        error_messages={
            "pattern": "Цвет должен быть в формате HEX (#RRGGBB), например: #FF0000",
            "type": "Цвет должен быть строкой"
        }
    )
    is_active: bool = Field(
        default=True,
        description="Статус активности типа тренировки",
        error_messages={
            "type": "Поле is_active должно быть булевым значением (true/false)"
        }
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Йога для начинающих",
                    "is_subscription_only": False,
                    "price": 15.99,
                    "color": "#FFFFFF",
                    "is_active": True
                },
                {
                    "name": "Фитнес",
                    "is_subscription_only": True,
                    "price": None,
                    "color": "#000000",
                    "is_active": True
                },
            ]
        }
    )

    @field_validator("price", mode="before")
    def validate_price(cls, value, info):
        is_subscription_only = info.data.get("is_subscription_only")
        if is_subscription_only is False and value is None:
            raise ValueError("Для тренировки без подписки необходимо указать цену")
        if is_subscription_only is True and value is not None:
            raise ValueError("Для тренировки по подписке цена должна быть пустой (None)")
        if value is not None and value < 0:
            raise ValueError("Цена не может быть отрицательной")
        return value

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Название тренировки не может быть пустым или состоять только из пробелов")
        return v.strip()

    @field_validator("color")
    def validate_color(cls, v: str) -> str:
        import re
        if not re.match("^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Неверный формат цвета. Используйте формат HEX (#RRGGBB), например: #FF0000")
        return v.upper()  # Приводим к верхнему регистру для единообразия


# Схема для обновления существующего типа тренировки
class TrainingTypeUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        min_length=2, 
        max_length=50, 
        description="Название типа тренировки (от 2 до 50 символов)",
        error_messages={
            "min_length": "Название тренировки должно содержать минимум 2 символа",
            "max_length": "Название тренировки не должно превышать 50 символов",
            "type": "Название тренировки должно быть строкой"
        }
    )
    is_subscription_only: Optional[bool] = Field(
        None,
        description="Флаг, указывающий, доступна ли тренировка только по подписке",
        error_messages={
            "type": "Поле is_subscription_only должно быть булевым значением (true/false)"
        }
    )
    price: Optional[float] = Field(
        None, 
        ge=0, 
        description="Цена тренировки (должна быть больше или равна 0)",
        error_messages={
            "ge": "Цена не может быть отрицательной",
            "type": "Цена должна быть числом"
        }
    )
    color: Optional[str] = Field(
        None, 
        pattern="^#[0-9A-Fa-f]{6}$", 
        description="Цвет в формате HEX (#RRGGBB)",
        error_messages={
            "pattern": "Цвет должен быть в формате HEX (#RRGGBB), например: #FF0000",
            "type": "Цвет должен быть строкой"
        }
    )
    is_active: Optional[bool] = Field(
        None,
        description="Статус активности типа тренировки",
        error_messages={
            "type": "Поле is_active должно быть булевым значением (true/false)"
        }
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Пилатес",
                    "is_subscription_only": True,
                    "price": 19.99,
                    "color": "#000000",
                    "is_active": True
                },
                {
                    "name": "Кроссфит",
                    "is_subscription_only": False,
                    "price": 25.00,
                    "color": "#FF5733",
                    "is_active": False
                },
            ]
        }
    )

    @field_validator("name")
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Название тренировки не может быть пустым или состоять только из пробелов")
        return v.strip()

    @field_validator("color")
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match("^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Неверный формат цвета. Используйте формат HEX (#RRGGBB), например: #FF0000")
        return v.upper()

    @field_validator("price")
    def validate_price(cls, v: Optional[float], info) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return v


# Схема для ответа на запросы типа тренировки
class TrainingTypeResponse(TrainingTypeBase):
    pass


# Схема для списка типов тренировок
class TrainingTypesList(BaseModel):
    training_types: list[TrainingTypeResponse]