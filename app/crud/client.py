from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import ClientCreate, ClientUpdate


# Создание клиента
def create_client(db: Session, client_data: ClientCreate):
    try:
        print("Подключённые таблицы:", db.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall())
        client = User(
            first_name=client_data.first_name,
            last_name=client_data.last_name,
            date_of_birth=client_data.date_of_birth,
            email=client_data.email,
            phone=client_data.phone,
            whatsapp_number=client_data.whatsapp_number,
            balance=client_data.balance,
            role=UserRole.CLIENT.value
        )

        db.add(client)
        db.commit()
        db.refresh(client)
        return client
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


# Получить клиента по ID
def get_client(db: Session, client_id: int):
    return db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()


# Получить всех клиентов
def get_all_clients(db: Session):
    return db.query(User).filter(User.role == UserRole.CLIENT).all()


# Обновление клиента
def update_client(db: Session, client_id: int, client_data: ClientUpdate):
    client = db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()
    if not client:
        return None
    for key, value in client_data.model_dump(exclude_unset=True).items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


# Удалить клиента
def delete_client(db: Session, client_id: int):
    client = db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()
    if not client:
        return None
    db.delete(client)
    db.commit()
    return client