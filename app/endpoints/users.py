from fastapi import HTTPException

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.auth.jwt_handler import verify_jwt_token
from app.entities.users.models import UserRoleEnum
import logging
from app.entities.users.models import User
from app.entities.users.schemas import AdminRead, ClientRead, TrainerRead
from typing import List, Union
from app.entities.users.crud import get_user_by_email




router = APIRouter()

logger = logging.getLogger(__name__)



@router.get("/me", response_model=Union[AdminRead, ClientRead, TrainerRead])
async def get_current_user(current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    logger.debug("EXECUTING")
    logger.debug(f"PAYLOAD = {current_user}")
    user = get_user_by_email(db, current_user["email"])
    if current_user["role"] == UserRoleEnum.ADMIN:
        return AdminRead.from_orm(user)
    elif current_user["role"] == UserRoleEnum.CLIENT:
        raise HTTPException(status_code=403, detail="Forbidden" )







