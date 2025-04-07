import datetime
from typing import Optional

from pydantic import BaseModel


class InvoiceRead(BaseModel):
    id: int
    amount: float
    invoice_type: str
    created_at: datetime.datetime
    paid_at: Optional[datetime.datetime] = None

    # Указываем, что объекты будут загружаться напрямую из моделей SQLAlchemy
    model_config = {"from_attributes": True}
