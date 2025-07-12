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


# Получить активных пользователей
def get_active_users(db: Session):
    return db.query(User).filter(User.is_active == True).order_by(User.first_name, User.last_name).all()


# Получить пользователей по роли
def get_users_by_role(db: Session, role: str):
    return db.query(User).filter(User.role == role).order_by(User.first_name, User.last_name).all()


# Обновить баланс пользователя
def update_user_balance(db: Session, user_id: int, new_balance: float):
    user = get_user_by_id(db, user_id)
    if user:
        user.balance = new_balance
        # НЕ делаем commit здесь - это делает сервис
        db.flush()
        db.refresh(user)
        return user
    return None


# Получить текущего пользователя
def get_user_me(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


# Удалить пользователя
def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False