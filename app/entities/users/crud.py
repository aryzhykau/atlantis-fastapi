from typing import Union

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import EmailStr
from datetime import datetime

from app.entities.pagination.schemas import PaginatedResponse
from app.entities.users.models import User
from app.entities.users.models import UserRoleEnum
from app.entities.users.schemas import ClientRead, ClientCreate, TrainerCreate, TrainerRead
import logging


logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: EmailStr):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, id: int):
    return db.query(User).filter(User.id == id).first()



def create_user(db: Session, user: Union[ClientCreate, TrainerCreate]):
    new_user_data = user.model_dump()
    new_user_data["created_at"] = datetime.utcnow()  # Устанавливаем текущую дату
    new_user = User(**new_user_data)
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()  # Откат транзакции

        # Извлекаем текст ошибки для анализа
        error_message = str(e.orig)

        # Проверяем нарушение уникальности по полям
        if "ix_users_phone" in error_message:
            raise HTTPException(status_code=400, detail="Пользователь с таким телефоном уже существует")
        elif "ix_users_email" in error_message:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        else:
            # Общая обработка для других уникальных полей
            raise HTTPException(status_code=500, detail="Произошла ошибка при сохранении пользователя")

    return new_user


def update_user(db: Session, user_id: int, user_updates: Union[ClientCreate, TrainerCreate]):
    existing_user = db.query(User).filter(User.id == user_id).first()

    if not existing_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    for attr, value in user_updates.model_dump().items():
        setattr(existing_user, attr, value)  # Обновляем атрибуты пользователя

    try:
        db.commit()
        db.refresh(existing_user)
    except IntegrityError as e:
        db.rollback()

        # Извлекаем текст ошибки для анализа
        error_message = str(e.orig)

        # Проверяем нарушение уникальности по полям
        if "ix_users_phone" in error_message:
            raise HTTPException(status_code=400, detail="Пользователь с таким телефоном уже существует")
        elif "ix_users_email" in error_message:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        else:
            raise HTTPException(status_code=500, detail="Произошла ошибка при обновлении пользователя")

    return existing_user


def get_all_users_by_role(db: Session, role: UserRoleEnum):
    users = db.query(User).filter(User.role == role.value).order_by(User.last_name, User.first_name).all()
    logger.debug(users)
    if role == UserRoleEnum.CLIENT:
        schema = ClientRead
    elif role == UserRoleEnum.TRAINER:
        schema = TrainerRead
    else:
        raise ValueError(f"Unsupported role: {role}")
    return [schema.model_validate(user) for user in users] if users else []

def get_users_by_role_paginated(db: Session, role: UserRoleEnum, page: int = 1, page_size: int = 10, ):
    offset = (page - 1) * page_size

    total_count = db.query(User).filter(User.role == role.value).count()
    total_pages = (total_count + page_size - 1) // page_size

    users = db.query(User).filter(User.role == role.value).offset(offset).limit(page_size).all()

    # Определяем, какую схему использовать
    if role == UserRoleEnum.CLIENT:
        schema = ClientRead
    elif role == UserRoleEnum.TRAINER:
        schema = TrainerRead
    else:
        raise ValueError(f"Unsupported role: {role}")

    users_data = [schema.model_validate(user) for user in users] if users else []

    return users_data

def delete_user_by_id(db: Session, user_id: int):
    # Ищем пользователя в базе по ID
    row_to_delete = db.query(User).filter(User.id == user_id).first()

    # Если пользователь не найден, возвращаем ошибку
    if not row_to_delete:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Удаляем найденного пользователя
    db.delete(row_to_delete)
    db.commit()

    return {"message": "Пользователь успешно удален"}











