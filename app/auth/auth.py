import os
import requests
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
import google.auth
from google.auth.transport.requests import Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import Optional
import logging

from app.dependencies import get_db
from app.entities.users.crud import get_user_by_email  # Функция для поиска пользователя в БД

logger = logging.getLogger(__name__)


load_dotenv()

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "317287995854-hjm52r9lvi0sungac6v5vbv2h2qr9cut.apps.googleusercontent.com")
JWT_SECRET = os.getenv("JWT_SECRET", "hingshfiuehrigdukyshekjxflhas;kou498xfmh")  # Лучше хранить в .env
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def get_user_info_from_access_token(authorization: str):
    try:
        # Проверка токена с использованием Google API
        access_token = authorization.replace("Bearer ", "").strip()

        response = requests.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid access token")

        user_info = response.json()  # Преобразуем ответ в JSON
        return {"email": user_info["email"], "name": user_info["name"], "picture": user_info["picture"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user info: {str(e)}")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """ Создаёт JWT access token """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def refresh_access_token(token: str):
    """ Проверяет токен и возвращает новый токен """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        new_token = create_access_token(
            data={"sub": email, "id": payload.get("id"), "role": payload.get("role")}
        )
        return new_token
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token is invalid or expired: {str(e)}")


@router.get("/google", response_model=TokenResponse)
async def auth_google(authorization: str = Header(...), db: Session = Depends(get_db)):
    logger.debug("Processing authorization")
    logger.debug(authorization)
    """ Проверяет Google ID Token, ищет пользователя в БД и выдаёт JWT """
    user_data = get_user_info_from_access_token(authorization)
    # Проверяем, есть ли пользователь в базе
    user = get_user_by_email(db, email=user_data["email"])
    if not user:
        raise HTTPException(status_code=403, detail="Access denied: user not found")
    logger.debug(user.role)
    # Генерируем access_token
    access_token = create_access_token(data={"sub": user.email, "id": user.id, "role": user.role})

    return {"access_token": access_token}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(token: str):
    """ Обновляет JWT токен """
    new_token = refresh_access_token(token)
    return {"access_token": new_token}
