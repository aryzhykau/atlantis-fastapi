import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.auth.permissions import get_current_user
from app.core.security import verify_api_key 
from app.dependencies import get_db
from app.schemas.user import ClientCreate, ClientResponse, ClientUpdate, StatusUpdate, ClientStatusResponse
from app.schemas.student import StudentResponse
from app.crud import client as crud_client
from app.crud import student as crud_student
from app.services.client_service import client_service

router = APIRouter(prefix="/forms", tags=["Form"])

logger = logging.getLogger(__name__)

@router.post("/clients", response_model=ClientResponse, status_code=201, dependencies=[Depends(verify_api_key)])
def create_client_endpoint(client_data: ClientCreate, db: Session = Depends(get_db)):
    try:
        logger.info("calling create user")
        return client_service.create_client_with_students(db, client_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
