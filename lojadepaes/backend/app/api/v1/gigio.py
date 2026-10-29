from fastapi import APIRouter, Header, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, DbSession, OptionalCustomer
from app.domain.admin_auth import SESSION_COOKIE, load_session
from app.domain.builder_tip import builder_tip
from app.domain.errors import ConfirmationError
from app.domain.gigio import rate_limit
from app.domain.gigio.service import chat, resolve_gateway, status_payload

router = APIRouter(prefix="/gigio", tags=["gigio"])


class GigioBuilderPageIn(BaseModel):
    flour: str = Field(default="", max_length=80)
    preparation: str = Field(default="", max_length=80)
    inclusions: list[str] = Field(default_factory=list, max_length=8)
    shape: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=200)


class GigioLibraryPageIn(BaseModel):
    article_id: str = Field(default="", max_length=80)
    article_version: int = Field(default=0)
    intent: str = Field(default="", max_length=20)
    calculator_mode: str = Field(default="", max_length=32)


class GigioPageIn(BaseModel):
    path: str = Field(default="", max_length=120)
    product_slug: str = Field(default="", max_length=80)
    recipe_slug: str = Field(default="", max_length=80)
    order_reference: str = Field(default="", max_length=40)
    consult: str = Field(default="", max_length=20)
    builder: GigioBuilderPageIn | None = None
    library: GigioLibraryPageIn | None = None


class GigioTipIn(BaseModel):
    flour_id: str = Field(default="", max_length=40)
    dough_id: str = Field(default="", max_length=40)
    ingredient_ids: list[str] = Field(default_factory=list, max_length=8)
    shape_id: str = Field(default="", max_length=40)
    free_text: str = Field(default="", max_length=200)
    occasion: str = Field(default="", max_length=200)
    context_text: str = Field(default="", max_length=400)


class GigioMessageIn(BaseModel):
    role: str = Field(min_length=1, max_length=16)
    content: str = Field(default="", max_length=4000)


class GigioChatIn(BaseModel):
    messages: list[GigioMessageIn] = Field(default_factory=list)
    page: GigioPageIn | None = None
    spend_credit: bool = False
    operation_id: str | None = Field(default=None, max_length=80)


@router.get("/status")
def gigio_status(settings: AppSettings, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    payload = status_payload(settings)
    return {
        "enabled": payload["enabled"],
        "ready": payload["ready"],
        "welcome": payload["welcome"],
        "starters": payload["starters"],
        "culinary": payload["culinary"],
        "rules_version": payload["rules_version"],
        "live": payload["provider"] == "bedrock",
        "provider": payload["provider"],
        "region": payload["region"],
        "model_family": payload["model_family"],
    }


@router.post("/chat")
def gigio_chat(
    payload: GigioChatIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    response: Response,
    account: OptionalCustomer,
    order_token: str | None = Header(default=None, alias="X-Order-Token"),
    session_token: str | None = None,
) -> dict:
    del session_token
    response.headers["Cache-Control"] = "no-store"
    host = request.client.host if request.client else "unknown"
    rate_limit.acquire(host)
    try:
        cookie = request.cookies.get(SESSION_COOKIE)
        admin = load_session(db, settings, cookie, rotate_csrf=False) is not None
        gateway = getattr(request.app.state, "gigio_gateway", None)
        return chat(
            db,
            settings,
            messages=[item.model_dump() for item in payload.messages],
            page=payload.page.model_dump() if payload.page else {},
            order_token=order_token,
            is_admin=admin,
            gateway=gateway,
            account=account,
            spend_credit=payload.spend_credit,
            operation_id=payload.operation_id,
        )
    finally:
        rate_limit.release()


@router.post("/builder-tip")
def gigio_builder_tip(
    payload: GigioTipIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    response: Response,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    if not settings.gigio_enabled:
        raise ConfirmationError("o Gigio não está disponível neste ambiente")
    host = request.client.host if request.client else "unknown"
    rate_limit.acquire(host)
    try:
        gateway = getattr(request.app.state, "gigio_gateway", None) or resolve_gateway(settings)
        return builder_tip(db, settings, payload.model_dump(), gateway)
    finally:
        rate_limit.release()
