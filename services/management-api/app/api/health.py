import asyncio
import logging
import redis

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db
from app.core.redis import redis_client


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    try:
        async with asyncio.timeout(2):
            await db.execute(select(1))

    except (SQLAlchemyError, OSError, TimeoutError):
        logger.exception("Readiness check failed: database is unavailable")
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    try:
        await redis_client.ping()
    except Exception:
        logger.exception("Readiness check failed: connection error")
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    return {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}