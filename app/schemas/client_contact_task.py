from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClientContactReason(str, Enum):
    NEW_CLIENT = "NEW_CLIENT"
    RETURNED = "RETURNED"


class ClientContactStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"


class ClientContactTaskCreate(BaseModel):
    client_id: int
    reason: ClientContactReason
    note: Optional[str] = Field(None, description="Примечание при создании")
    assigned_to_id: Optional[int] = None
    last_activity_at: Optional[datetime] = None


class ClientContactTaskUpdate(BaseModel):
    status: Optional[ClientContactStatus] = None
    note: Optional[str] = None
    assigned_to_id: Optional[int] = None


class ClientContactTaskResponse(BaseModel):
    id: int
    client_id: int
    reason: ClientContactReason
    status: ClientContactStatus
    created_at: datetime
    done_at: Optional[datetime] = None
    assigned_to_id: Optional[int] = None
    note: Optional[str] = None
    last_activity_at: Optional[datetime] = None

    class Config:
        from_attributes = True



