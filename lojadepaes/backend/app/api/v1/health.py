import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter()
logger = logging.getLogger("lojadepaes.health")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("PostgreSQL indisponível no readiness")
        raise HTTPException(
            status_code=503,
            detail=ReadyResponse(status="unavailable").model_dump(),
        ) from None
    except Exception:
        logger.warning("Falha ao verificar PostgreSQL no readiness")
        raise HTTPException(
            status_code=503,
            detail=ReadyResponse(status="unavailable").model_dump(),
        ) from None
    return ReadyResponse(status="ok")
