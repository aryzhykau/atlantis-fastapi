# Atlantis FastAPI Project

## Описание проекта
Atlantis - это бэкенд-приложение на FastAPI, предназначенное для управления фитнес-центром или спортивной школой. Система обеспечивает управление пользователями, тренировками, подписками и взаимодействием между тренерами и студентами.

## Текущий функционал

### Управление пользователями

#### Клиенты и Студенты
- ✅ Базовая модель клиента с валидацией данных
- ✅ CRUD операции для клиентов
- ✅ Управление статусом клиента (активация/деактивация)
- ✅ Базовая модель студента
- ✅ CRUD операции для студентов
- ✅ Связь клиент-студент (один клиент может иметь несколько студентов)
- ✅ Возможность клиенту быть студентом
- ✅ Управление балансом клиента

#### Тренеры
- ✅ Базовая модель тренера
- ✅ CRUD операции для тренеров
- ✅ Расширенная валидация данных:
  - Валидация телефона (10-15 цифр)
  - Валидация email
  - Валидация имени/фамилии (2-50 символов, только буквы)
  - Валидация зарплаты (не отрицательная, для фиксированной - не нулевая)
- ✅ Управление статусом тренера:
  - Активация/деактивация
  - Автоматическое отслеживание даты деактивации
- ✅ Полное тестовое покрытие функционала тренеров

### Тренировки

#### Типы тренировок
- ✅ Базовая модель типа тренировки
- ✅ CRUD операции для типов тренировок

#### Шаблоны тренировок
- ✅ Базовая модель шаблона тренировки
- ✅ CRUD операции для шаблонов

### Безопасность
- ✅ Базовая аутентификация
- ✅ Авторизация по ролям (ADMIN, TRAINER, CLIENT)

## Технический стек
- FastAPI
- PostgreSQL
- SQLAlchemy (ORM)
- Alembic (миграции)
- JWT (аутентификация)
- Docker
- Poetry (управление зависимостями)

## Структура проекта

```
app/
├── models/         # SQLAlchemy модели
├── schemas/        # Pydantic схемы
├── crud/          # CRUD операции
├── endpoints/      # API эндпоинты
├── auth/          # Аутентификация
├── utils/         # Вспомогательные функции
└── errors/        # Обработка ошибок
```

# Руководство по разработке

## 1. Структура моделей (SQLAlchemy Models)

### 1.1. Расположение
```
app/models/
```

### 1.2. Правила создания моделей

1. **Базовый класс**:
```python
from app.database import Base
from sqlalchemy import Column, Integer, String, Date, Boolean, Enum, Float

class YourModel(Base):
    __tablename__ = "your_table_name"
```

2. **Типы полей**:
- `Integer`: для числовых ID и целочисленных значений
- `String`: для текстовых полей
- `Date`: для дат
- `Boolean`: для логических значений
- `Float`: для чисел с плавающей точкой
- `Enum`: для перечислений
- `ForeignKey`: для связей между таблицами

3. **Обязательные поля**:
```python
id = Column(Integer, primary_key=True, index=True)
```

4. **Валидация**:
```python
from sqlalchemy.orm import validates

@validates("field_name")
def validate_field(self, key, value):
    # Логика валидации
    return value
```

5. **Связи**:
```python
from sqlalchemy.orm import relationship

related_items = relationship("RelatedModel", back_populates="parent")
```

## 2. Pydantic Схемы

### 2.1. Расположение
```
app/schemas/
```

### 2.2. Правила создания схем

1. **Базовые схемы**:
```python
from pydantic import BaseModel

class ModelBase(BaseModel):
    model_config = {"from_attributes": True}
```

2. **Типы схем**:
- `Create`: для создания объекта
- `Update`: для обновления объекта
- `Response`: для ответа API
- `Base`: базовые поля

3. **Структура схем**:
```python
# Схема создания
class ModelCreate(BaseModel):
    required_field: str
    optional_field: str | None = None

# Схема обновления
class ModelUpdate(BaseModel):
    field: str | None = None

# Схема ответа
class ModelResponse(ModelBase):
    id: int
    field: str
```

4. **Валидация**:
```python
from pydantic import EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    
    @validator("field_name")
    def validate_field(cls, v):
        if not valid:
            raise ValueError("Validation message")
        return v
```

## 3. CRUD Операции

### 3.1. Расположение
```
app/crud/
```

### 3.2. Правила создания CRUD операций

1. **Базовая структура**:
```python
from sqlalchemy.orm import Session
from app.models import Model
from app.schemas import ModelCreate, ModelUpdate

def get_by_id(db: Session, id: int):
    return db.query(Model).filter(Model.id == id).first()

def create(db: Session, data: ModelCreate):
    db_item = Model(**data.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update(db: Session, id: int, data: ModelUpdate):
    db_item = get_by_id(db, id)
    if db_item:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete(db: Session, id: int):
    db_item = get_by_id(db, id)
    if db_item:
        db.delete(db_item)
        db.commit()
    return db_item
```

## 4. Endpoints (API Routes)

### 4.1. Расположение
```
app/endpoints/
```

### 4.2. Правила создания эндпоинтов

1. **Базовая структура**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas import ModelCreate, ModelUpdate, ModelResponse
from app.crud import crud_functions

router = APIRouter(prefix="/resource", tags=["Resource"])

@router.get("/{id}", response_model=ModelResponse)
def get_item(id: int, db: Session = Depends(get_db)):
    item = crud_functions.get_by_id(db, id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item

@router.post("/", response_model=ModelResponse)
def create_item(data: ModelCreate, db: Session = Depends(get_db)):
    return crud_functions.create(db, data)

@router.put("/{id}", response_model=ModelResponse)
def update_item(id: int, data: ModelUpdate, db: Session = Depends(get_db)):
    item = crud_functions.update(db, id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item

@router.delete("/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    item = crud_functions.delete(db, id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted successfully"}
```

### 4.3. Важные моменты:

1. **Зависимости**:
```python
from app.dependencies import get_db
db: Session = Depends(get_db)
```

2. **Авторизация**:
```python
from app.auth.jwt_handler import verify_jwt_token
current_user = Depends(verify_jwt_token)
```

3. **Обработка ошибок**:
```python
from fastapi import HTTPException

if not item:
    raise HTTPException(status_code=404, detail="Not found")
```

## 5. Рекомендации по именованию

1. **Модели**: 
   - Имя в единственном числе
   - PascalCase
   - Пример: `User`, `TrainingTemplate`

2. **Таблицы**:
   - Имя во множественном числе
   - snake_case
   - Пример: `users`, `training_templates`

3. **Схемы**:
   - Суффиксы: `Create`, `Update`, `Response`
   - Пример: `UserCreate`, `UserUpdate`, `UserResponse`

4. **CRUD функции**:
   - Префиксы: `get_`, `create_`, `update_`, `delete_`
   - Пример: `get_user_by_id`, `create_user`

5. **Эндпоинты**:
   - REST-совместимые пути
   - Пример: `/users/{id}`, `/training-templates/`

## 6. Миграции (Alembic)

1. **Создание миграции**:
```bash
alembic revision --autogenerate -m "description"
```

2. **Применение миграций**:
```bash
alembic upgrade head
```

## Запуск проекта

### Локальная разработка

1. Установка зависимостей:
```bash
poetry install
```

2. Настройка переменных окружения:
```bash
cp .envdev .env
```

3. Запуск базы данных:
```bash
docker-compose up -d db
```

4. Применение миграций:
```bash
alembic upgrade head
```

5. Запуск сервера разработки:
```bash
uvicorn app.main:app --reload
```

### Docker

Запуск всего проекта в Docker:
```bash
docker-compose up -d
```

## API Документация

После запуска проекта, документация API доступна по следующим URL:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
