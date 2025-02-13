from authlib.jose import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.auth import JWT_SECRET, JWT_ALGORITHM
import logging
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/google")


def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    logger.debug("EXECUTING")
    """ Проверяет JWT access token """
    try:
        payload = jwt.decode(token, JWT_SECRET)

        logger.debug(f"payload = {payload}")
        return {"email": payload["sub"], "role": payload["role"], "id": payload["id"]}
    except :
        raise HTTPException(status_code=401, detail="Error")



# security = HTTPBearer()
#
# def verify_user(credentials: HTTPAuthorizationCredentials = Security(security)):
#     token = credentials.credentials
#     return verify_jwt_token(token)