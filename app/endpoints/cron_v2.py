"""Cron-эндпоинты v2, защищены X-API-Key."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.dependencies import get_db
from app.services.subscription_v2 import process_auto_renewals_v2, process_overdue_invoices_v2
from app.services.daily_operations_v2 import DailyOperationsServiceV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/cron", tags=["Cron v2"])


@router.post("/process-overdue-invoices", dependencies=[Depends(verify_api_key)])
def process_overdue_invoices_endpoint(db: Session = Depends(get_db)):
    """Переводит просроченные PENDING SUBSCRIPTION инвойсы → UNPAID (или PAID если баланс есть).
    Запускается ежедневно в 08:00.
    """
    result = process_overdue_invoices_v2(db)
    return {**result, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/auto-renewal", dependencies=[Depends(verify_api_key)])
def auto_renewal_v2_endpoint(db: Session = Depends(get_db)):
    """Создаёт абонементы на следующий месяц для is_auto_renew подписчиков.
    Запускается ежедневно в 02:00, срабатывает только в последний день месяца.
    """
    result = process_auto_renewals_v2(db)
    return {**result, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/process-daily-operations", dependencies=[Depends(verify_api_key)])
def process_daily_operations_v2_endpoint(db: Session = Depends(get_db)):
    """Обрабатывает is_subscription_only тренировки текущего дня (создание MissedSession).
    Запускается ежедневно в 01:00.
    """
    service = DailyOperationsServiceV2(db)
    result = service.process_daily_operations_v2()
    return {**result, "timestamp": datetime.now(timezone.utc).isoformat()}
