from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.dependencies import get_db
from app.core.security import verify_api_key
from app.auth.permissions import get_current_user
from app.models import User, UserRole
from app.services.subscription import SubscriptionService


from app.services.daily_operations import DailyOperationsService
from app.services.financial import FinancialService
from app.services.client_contact import ClientContactService
from app.services.trainer_salary import TrainerSalaryService
from datetime import date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])




@router.post("/auto-renewal", dependencies=[Depends(verify_api_key)])
def auto_renewal_subscriptions_endpoint(db: Session = Depends(get_db)):
    """
    Автоматическое продление всех абонементов с автопродлением, которые заканчиваются сегодня.
    Защищен API ключом (передается в заголовке X-API-Key).
    Может вызываться внешним сервисом по расписанию (например, cron).
    """
    try:
        subscription_service = SubscriptionService(db)
        renewed_subscriptions = subscription_service.process_auto_renewals()
        
        return {
            "message": "Auto renewals processed",
            "renewed_count": len(renewed_subscriptions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in auto renewals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-unfreeze", dependencies=[Depends(verify_api_key)])
def auto_unfreeze_subscriptions_endpoint(db: Session = Depends(get_db)):
    """
    Автоматическая разморозка всех абонементов с истёкшей заморозкой.
    Защищен API ключом (передается в заголовке X-API-Key).
    Может вызываться внешним сервисом по расписанию (например, cron).
    """
    try:
        subscription_service = SubscriptionService(db)
        unfrozen_subscriptions = subscription_service.auto_unfreeze_expired_subscriptions()
        
        return {
            "message": "Auto unfreeze completed",
            "unfrozen_count": len(unfrozen_subscriptions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in auto unfreeze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-invoices")
def process_invoices_endpoint(
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db),
):
    """Обработка инвойсов"""
    
    try:
        financial_service = FinancialService(db)
        result = financial_service.process_invoices(current_user["id"])
        
        return {
            "message": "Invoice processing completed",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in invoice processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


 


@router.post("/process-daily-operations", dependencies=[Depends(verify_api_key)])
def process_daily_operations_endpoint(db: Session = Depends(get_db)):
    """
    Запускает ежедневный процесс:
    - Обработка посещаемости за сегодня (REGISTERED -> PRESENT)
    - Финансовая обработка тренировок на завтра (списание занятий/инвойсы)
    """
    try:
        service = DailyOperationsService(db)
        result = service.process_daily_operations()
        
        return {
            "status": "success", 
            "message": "Daily operations completed successfully",
            "attendance_marking_students_updated": result.get("marked_students_present"),
            "financial_processing_students_updated": result.get("students_updated_financial"),
            "financial_processing_trainings_processed": result.get("trainings_processed_financial"),
            "financial_processing_date": result.get("processing_date_financial"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in daily operations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 


@router.post("/detect-returned-clients", dependencies=[Depends(verify_api_key)])
def detect_returned_clients_endpoint(db: Session = Depends(get_db)):
    """
    Детектит клиентов, вернувшихся после периода неактивности (>= 30 дней),
    и создаёт для них PENDING-задачи контакта с reason=RETURNED.
    """
    try:
        service = ClientContactService(db)
        created = service.detect_and_create_returned_clients_tasks()
        db.commit()
        return {
            "message": "Detection completed",
            "created": created,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in detect-returned-clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/finalize-salaries", dependencies=[Depends(verify_api_key)])
def finalize_salaries_endpoint(
    processing_date: date,
    db: Session = Depends(get_db),
):
    """
    Finalize per-training salaries for a given date.

    Protected by API key (X-API-Key). Intended to be called by a scheduler.
    Uses processed_by_id=0 to indicate the system process.
    """
    try:
        service = TrainerSalaryService(db)
        result = service.finalize_salaries_for_date(processing_date=processing_date, processed_by_id=0)

        return {
            "message": "Salaries finalized",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in finalize-salaries cron: {e}")
        raise HTTPException(status_code=500, detail=str(e))