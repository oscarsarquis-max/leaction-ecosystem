from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import AppSettings, CustomerUser, DbSession, OptionalCustomer
from app.domain.baker_library.access import (
    access_for_account,
    cancel_subscription,
    public_plan,
    start_subscription_checkout,
)
from app.domain.baker_library.articles import list_public_articles, public_article
from app.domain.baker_library.calculator import compute
from app.domain.customer_identity import (
    public_account_view,
    set_customer_cookie,
    start_resume,
    start_resume_by_cpf,
    start_signup,
    verify_code,
)

router = APIRouter(prefix="/biblioteca", tags=["biblioteca"])


class CalculatorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "from_flour"
    flour_g: float | None = None
    target_flour_g: float | None = None
    target_dough_g: float | None = None
    hydration_pct: float
    salt_pct: float
    preferment_flour_pct: float | None = None
    levain_weight_g: float | None = None
    levain_hydration_pct: float
    levain_mode: str = "pff"
    extras: list[dict[str, Any]] = Field(default_factory=list)


class IdentifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=254)
    cpf: str = Field(default="", max_length=14)


class VerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(default="", max_length=254)
    cpf: str = Field(default="", max_length=14)
    code: str = Field(min_length=4, max_length=8)


class CheckoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    return_to: str = Field(default="/#biblioteca", max_length=160)
    sku: str = Field(default="", max_length=80)


@router.get("/artigos")
def biblioteca_artigos(db: DbSession) -> dict:
    return {"items": list_public_articles(db), "calculator_href": "/biblioteca/calculadora"}


@router.get("/artigos/{slug}")
def biblioteca_artigo(slug: str, db: DbSession) -> dict:
    return public_article(db, slug)


@router.post("/calculadora")
def biblioteca_calculadora(payload: CalculatorIn) -> dict:
    return compute(payload.model_dump())


@router.get("/plano")
def biblioteca_plano(settings: AppSettings, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return public_plan(settings)


@router.get("/acesso")
def biblioteca_acesso(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    account: OptionalCustomer,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return access_for_account(db, settings, account)


@router.post("/identificar")
def biblioteca_identificar(payload: IdentifyIn, db: DbSession, settings: AppSettings) -> dict:
    if payload.cpf.strip() and payload.name.strip():
        return start_signup(db, settings, payload.name, payload.email, payload.cpf)
    if payload.cpf.strip():
        return start_resume_by_cpf(db, settings, payload.cpf)
    return start_resume(db, settings, payload.email)


@router.post("/verificar")
def biblioteca_verificar(
    payload: VerifyIn, db: DbSession, settings: AppSettings, response: Response
) -> dict:
    account, token = verify_code(
        db,
        settings,
        payload.email,
        payload.code,
        enroll_fidelity=False,
        cpf=payload.cpf,
    )
    set_customer_cookie(response, settings, token)
    return {
        "ok": True,
        **public_account_view(account, settings),
        **access_for_account(db, settings, account),
    }


@router.post("/assinatura")
def biblioteca_assinatura(
    payload: CheckoutIn,
    db: DbSession,
    settings: AppSettings,
    account: CustomerUser,
    response: Response,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return start_subscription_checkout(
        db, settings, account, return_to=payload.return_to, sku=payload.sku
    )


@router.post("/assinatura/cancelar")
def biblioteca_cancelar_assinatura(
    payload: CheckoutIn,
    settings: AppSettings,
    account: CustomerUser,
    response: Response,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return cancel_subscription(settings, account, payload.sku)
