from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
