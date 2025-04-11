import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.entities.invoices.crud import get_all_invoices
from app.entities.invoices.schemas import InvoiceRead
from app.entities.users.models import UserRoleEnum

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[InvoiceRead])
def get_invoices(
        user_id: Optional[int] = Query(None, description="Фильтр по ID пользователя"),
        only_unpaid: Optional[bool] = Query(None, description="Фильтр для получения только неоплаченных счетов"),
        current_user = Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    logger.debug(f"{only_unpaid, user_id}")
    if current_user["role"] == UserRoleEnum.ADMIN:
        invoices = get_all_invoices(db, user_id, only_unpaid)
        return [InvoiceRead.model_validate(invoice) for invoice in invoices]
    else:
        raise HTTPException(status_code=403, detail="Forbidden")