import logging
from datetime import datetime, timedelta
from typing import Union

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.entities.clients.crud import create_client
from app.entities.users.errors import UserNotFoundError
from app.entities.users.models import User
from app.entities.users.models import UserRoleEnum
from app.entities.users.schemas import ClientCreate, TrainerCreate, TrainerRead, \
    UserRead, ClientUserCreate, ClientUserRead
from app.entities.users.utils import check_existing_user_email, check_existing_user_phone

logger = logging.getLogger(__name__)






def get_user_by_email(db: Session, email: EmailStr) -> UserRead:
    logger.debug(f"EMAIL = {email}")
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise UserNotFoundError
    return UserRead.model_validate(db_user)

def get_client_by_id(db: Session, client_id: int) -> ClientUserRead:
    return ClientUserRead.model_validate(db.query(User).filter(User.id == client_id).first())

def get_client_users(db: Session) -> list[ClientUserRead]:
    return [ClientUserRead.model_validate(db.query(User).filter_by(role=UserRoleEnum.CLIENT).all())]


def create_client_user(db: Session, client: ClientUserCreate):
    try:

        #Checks before start creation of the UserModel in db
        check_existing_user_email(db, client.email)
        check_existing_user_phone(db, client.phone)

        new_user_client = client.model_dump()

        #Main User creation process
        new_user_client["created_at"] = new_user_client["updated_at"] = datetime.now()
        db_client = User(**new_user_client)
        db.add(db_client)
        db.flush()

        #Creationg a client model
        if new_user_client["is_client"]:

            new_user_client["clients"].append(ClientCreate(
                first_name=new_user_client["first_name"],
                last_name=new_user_client["last_name"],
                birth_date=new_user_client["birth_date"],
            ))

        for client in new_user_client["clients"]:
            create_client(db, db_client.id, client)

        db.commit()
        db.refresh(db_client)
        return db_client
    except Exception as e:
        db.rollback()
        raise e


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
    users = db.query(User).filter(User.role == role.value).options(joinedload(User.active_subscription)).order_by(User.last_name, User.first_name).all()
    logger.debug(users)
    if role == UserRoleEnum.CLIENT:
        schema = ClientUserRead
    elif role == UserRoleEnum.TRAINER:
        schema = TrainerRead
    else:
        raise ValueError(f"Unsupported role: {role}")
    logger.debug(users)
    return [schema.model_validate(user) for user in users] if users else []


# def delete_user_by_id(db: Session, user_id: int):
#     # Ищем пользователя в базе по ID
#     row_to_delete = db.query(User).filter(User.id == user_id).first()
#
#     # Если пользователь не найден, возвращаем ошибку
#     if not row_to_delete:
#         raise HTTPException(status_code=404, detail="Пользователь не найден")
#
#     # Удаляем найденного пользователя
#     db.delete(row_to_delete)
#     db.commit()
#
#     return {"message": "Пользователь успешно удален"}
