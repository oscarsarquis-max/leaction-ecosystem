from fastapi import APIRouter, Response

from app.api.deps import AppSettings
from app.domain.operations import operations_payload

router = APIRouter(tags=["operations"])


@router.get("/operations")
def get_operations(settings: AppSettings, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return operations_payload(settings)
