from fastapi import Security, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from app.core.config import CRON_API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Проверяет API ключ для cron-эндпоинтов.
    Использование:
    @router.get("/endpoint", dependencies=[Depends(verify_api_key)])
    """
    if not api_key or api_key != CRON_API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Could not validate API key"
        )
    return api_key 