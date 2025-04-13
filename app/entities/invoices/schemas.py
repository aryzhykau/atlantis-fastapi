import datetime
from typing import Optional

from pydantic import BaseModel

from app.entities.invoices.models import InvoiceTypeEnum
from app.entities.users.schemas import ClientRead


class InvoiceCreate(BaseModel):
    user_id: int
    invoice_type: InvoiceTypeEnum
    created_at: Optional[datetime.datetime] = None
    amount: int
    client_subscription_id: Optional[int] = None

class InvoiceRead(BaseModel):
    id: int
    amount: int
    invoice_type: InvoiceTypeEnum
    user: ClientRead
    client_subscription_id: Optional[int] = None
    created_at: datetime.datetime
    paid_at: Optional[datetime.datetime] = None

    # Указываем, что объекты будут загружаться напрямую из моделей SQLAlchemy
    model_config = {"from_attributes": True}
