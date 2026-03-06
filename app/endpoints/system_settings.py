"""Эндпоинты для системных настроек (system settings)."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.models import SystemSettings
from app.schemas.subscription_v2 import SystemSettingResponse, SystemSettingUpdate
from app.crud.subscription_v2 import set_system_setting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/system-settings", tags=["System Settings"])

ALLOWED_KEYS = {"makeup_window_days", "debt_behavior"}


@router.get("", response_model=List[SystemSettingResponse])
def get_system_settings_endpoint(
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db),
):
    """Получить все системные настройки."""
    settings = db.query(SystemSettings).all()
    return settings


@router.patch("", response_model=SystemSettingResponse)
def update_system_setting_endpoint(
    data: SystemSettingUpdate,
    current_user=Depends(get_current_user(["OWNER"])),
    db: Session = Depends(get_db),
):
    """Обновить системную настройку (только OWNER)."""
    if data.key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {data.key}")

    setting = set_system_setting(db, key=data.key, value=data.value, updated_by_id=current_user.id)
    db.commit()
    return setting
