from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.dependencies import get_db
from app.core.security import verify_api_key
from app.models import User, UserRole
from app.services.subscription import SubscriptionService
from app.services.training_processing import TrainingProcessingService
from app.services.daily_operations import DailyOperationsService

router = APIRouter(prefix="/cron", tags=["cron"])

@router.post("/check-auto-renewals", dependencies=[Depends(verify_api_key)])
def check_auto_renewals(db: Session = Depends(get_db)):
    """
    Эндпоинт для проверки и обработки автопродлений абонементов.
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

        # Запускаем проверку автопродлений
        service = SubscriptionService(db)
        renewed_subscriptions = service.process_auto_renewals(admin.id)
        
        return {
            "success": True,
            "renewals_processed": len(renewed_subscriptions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


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