from sqlalchemy.orm import Session
from app.models import User


# Получить пользователя по ID
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


# Получить пользователя по email
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


# Получить всех пользователей для автокомплита
def get_all_users(db: Session):
    return db.query(User).order_by(User.first_name, User.last_name).all()


# Удалить пользователя
def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


# Получить текущего пользователя
def get_user_me(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()