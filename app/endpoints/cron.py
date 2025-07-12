from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.dependencies import get_db
from app.core.security import verify_api_key, verify_jwt_token
from app.models import User, UserRole
from app.services.subscription import SubscriptionService
from app.services.training_processing import TrainingProcessingService
from app.services.daily_operations import DailyOperationsService
from app.services.invoice import InvoiceService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])

@router.post("/auto-mark-attendance")
def auto_mark_attendance_endpoint(
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Автоматическая отметка посещаемости"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        training_processing_service = TrainingProcessingService(db)
        result = training_processing_service.auto_mark_attendance(current_user["id"])
        
        return {
            "message": "Auto attendance marking completed",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in auto mark attendance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-auto-renewals")
def process_auto_renewals_endpoint(
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Обработка автопродления абонементов"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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


@router.post("/auto-unfreeze-subscriptions")
def auto_unfreeze_subscriptions_endpoint(
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Автоматическая разморозка абонементов"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Обработка инвойсов"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        invoice_service = InvoiceService(db)
        result = invoice_service.process_invoices(current_user["id"])
        
        return {
            "message": "Invoice processing completed",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in invoice processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-invoices", dependencies=[Depends(verify_api_key)])
def generate_invoices(db: Session = Depends(get_db)):
    """
    Эндпоинт для генерации инвойсов за тренировки на завтра.
    Защищен API ключом (передается в заголовке X-API-Key).
    Может вызываться внешним сервисом по расписанию (например, Google Apps Script).
    """
    try:
        # Получаем системного администратора
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            return {
                "success": False,
                "error": "No admin user found in the system",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Запускаем генерацию инвойсов
        service = TrainingProcessingService(db)
        result = service.process_tomorrow_trainings(admin.id)
        
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 


@router.post("/process-daily-operations", dependencies=[Depends(verify_api_key)])
def process_daily_operations_endpoint(db: Session = Depends(get_db)):
    """
    Запускает ежедневный процесс:
    - Обработка посещаемости за сегодня (REGISTERED -> PRESENT)
    - Финансовая обработка тренировок на завтра (списание занятий/инвойсы)
    """
    service = DailyOperationsService(db)
    service.process_daily_operations()
    return {"status": "success", "message": "Daily operations processing started."} 