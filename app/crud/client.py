from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas import ClientCreate, ClientUpdate


def create_client(db: Session, client_data: ClientCreate) -> User:
    """Creates a new client user in the database without committing."""
    client = User(
        first_name=client_data.first_name,
        last_name=client_data.last_name,
        date_of_birth=client_data.date_of_birth,
        email=client_data.email,
        phone_country_code=client_data.phone_country_code,
        phone_number=client_data.phone_number,
        whatsapp_country_code=client_data.whatsapp_country_code,
        whatsapp_number=client_data.whatsapp_number,
        balance=0,
        role=UserRole.CLIENT,
        is_authenticated_with_google=True  # Assuming default, can be changed by a service
    )
    db.add(client)
    db.flush()  # Flush to assign an ID to the client object
    return client


def get_client_by_id(db: Session, client_id: int) -> User | None:
    """Retrieves a client by their ID."""
    return db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()


def get_all_clients(db: Session) -> list[User]:
    """Retrieves all clients from the database."""
    return db.query(User).filter(User.role == UserRole.CLIENT).order_by(User.first_name, User.last_name).all()


def update_client(db: Session, client_id: int, client_data: ClientUpdate) -> User | None:
    """Updates a client's data without committing."""
    client = get_client_by_id(db, client_id)
    if not client:
        return None
    for key, value in client_data.model_dump(exclude_unset=True).items():
        setattr(client, key, value)
    return client


def delete_client(db: Session, client_id: int) -> User | None:
    """Deletes a client without committing."""
    client = get_client_by_id(db, client_id)
    if not client:
        return None
    db.delete(client)
    return client
