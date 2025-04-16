import datetime
from pydantic import BaseModel


class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: datetime.datetime
    is_active: bool = True
    has_trial: bool = True



class ClientRead(ClientCreate):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime