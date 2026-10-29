from fastapi import APIRouter, Query

from app.modules.login_editorial.service import static_payload, unavailable_fallback

router = APIRouter()


@router.get("/api/v1/public/login-editorial")
def get_login_editorial(mode: str | None = Query(default=None)) -> dict:
    if mode == "unavailable":
        return unavailable_fallback()
    if mode == "invalid":
        return {"schema_version": 99, "columns": [{"title": ""}]}
    return static_payload()
