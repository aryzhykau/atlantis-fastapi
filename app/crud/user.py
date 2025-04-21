from sqlalchemy.orm import Session
from app.models import User


# Получить пользователя по ID
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


# Получить пользователя по email
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


# Удалить пользователя (роль неважна)
def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    db.delete(user)
    db.commit()
    return user


# Получить текущего пользователя
def get_user_me(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()