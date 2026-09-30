from fastapi import APIRouter, Cookie, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    AdminUser,
    AppSettings,
    CustomerUser,
    DbSession,
    OptionalCustomer,
)
from app.domain.customer_identity import (
    CUSTOMER_COOKIE,
    clear_customer_cookie,
    logout_customer,
    public_account_view,
    set_customer_cookie,
    start_resume,
    start_signup,
    verify_code,
    verify_link,
)
from app.domain.house_fidelity import (
    activate_campaign,
    current_campaign,
    reward_catalog,
    reward_gaps,
    status_payload,
)
from app.domain.house_fidelity_redeem import eligible_500g_variants, redeem_loaf, redeem_review
from app.domain.storefront_orders import public_order_view

router = APIRouter(prefix="/promotions/house-fidelity", tags=["promotions"])


class SignupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=254)
    cpf: str = Field(min_length=11, max_length=14)


class ResumeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)


class VerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=4, max_length=8)


class RedeemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    requested_date: str
    idempotency_key: str = Field(min_length=8, max_length=120)
    preferred_time: str | None = None
    customer_note: str = ""
    delivery_street: str = ""
    delivery_number: str = ""
    delivery_complement: str = ""
    delivery_district: str = ""
    delivery_city: str = ""
    delivery_state: str = ""
    delivery_postal_code: str = ""


@router.get("")
def house_fidelity_status(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    account: OptionalCustomer,
    demo: str | None = None,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    payload = status_payload(db, settings, demo=demo, account=account)
    if account is not None:
        payload["cpf_masked"] = public_account_view(
            account, settings, campaign=current_campaign(db)
        )["cpf_masked"]
        payload["name"] = account.name
    return payload


@router.post("/signup")
def house_fidelity_signup(payload: SignupIn, db: DbSession, settings: AppSettings) -> dict:
    return start_signup(db, settings, payload.name, payload.email, payload.cpf)


@router.post("/resume")
def house_fidelity_resume(payload: ResumeIn, db: DbSession, settings: AppSettings) -> dict:
    return start_resume(db, settings, payload.email)


@router.post("/verify")
def house_fidelity_verify(
    payload: VerifyIn, db: DbSession, settings: AppSettings, response: Response
) -> dict:
    account, token = verify_code(db, settings, payload.email, payload.code)
    set_customer_cookie(response, settings, token)
    campaign = current_campaign(db)
    return {
        **status_payload(db, settings, account=account),
        **public_account_view(account, settings, campaign=campaign),
        "ok": True,
    }


@router.post("/verify-link")
def house_fidelity_verify_link(
    token: str, db: DbSession, settings: AppSettings, response: Response
) -> dict:
    account, raw = verify_link(db, settings, token)
    set_customer_cookie(response, settings, raw)
    campaign = current_campaign(db)
    return {
        **status_payload(db, settings, account=account),
        **public_account_view(account, settings, campaign=campaign),
        "ok": True,
    }


@router.post("/logout")
def house_fidelity_logout(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    session_token: str | None = Cookie(alias=CUSTOMER_COOKIE, default=None),
) -> dict:
    logout_customer(db, settings, session_token)
    clear_customer_cookie(response, settings)
    return {"ok": True}


@router.get("/me")
def house_fidelity_me(db: DbSession, settings: AppSettings, account: CustomerUser) -> dict:
    return {
        **status_payload(db, settings, account=account),
        **public_account_view(account, settings, campaign=current_campaign(db)),
    }


@router.get("/rewards")
def house_fidelity_rewards(db: DbSession, settings: AppSettings, account: CustomerUser) -> dict:
    del account
    return {
        "items": eligible_500g_variants(db),
        "gaps": reward_gaps(db),
        "campaign_active": status_payload(db, settings)["campaign_active"],
    }


@router.get("/redeem/review")
def house_fidelity_redeem_review(variant_id: str, account: CustomerUser, db: DbSession) -> dict:
    del account
    return redeem_review(db, variant_id)


@router.post("/redeem")
def house_fidelity_redeem(
    payload: RedeemIn, db: DbSession, settings: AppSettings, account: CustomerUser
) -> dict:
    order, token = redeem_loaf(db, settings, account, payload.model_dump())
    view = public_order_view(db, order)
    view["access_token"] = token
    return view


class AdjustIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    kind: str = Field(pattern="^(grant|reverse)$")
    reason: str = Field(min_length=1, max_length=280)
    credit_id: str | None = None


@router.get("/admin/participants")
def admin_participants(
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    q: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    del principal
    from app.domain.house_fidelity_admin import list_participants
    from app.domain.house_fidelity_ledger import pending_partial_reviews

    payload = list_participants(db, settings, query=q, page=page, page_size=page_size)
    campaign = current_campaign(db)
    reviews = pending_partial_reviews(db, campaign.id) if campaign is not None else []
    return {
        **payload,
        "gaps": reward_gaps(db),
        "catalog": reward_catalog(db),
        "pending_reviews": reviews,
    }


@router.get("/admin/participants/{account_id}")
def admin_participant_detail(
    account_id: str, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    from app.domain.house_fidelity_admin import participant_detail

    return participant_detail(db, settings, account_id)


@router.post("/admin/activate")
def admin_activate_campaign(db: DbSession, settings: AppSettings, principal: AdminUser) -> dict:
    del principal
    campaign = activate_campaign(db, settings)
    return {
        "ok": True,
        "status": campaign.status,
        "starts_at": campaign.starts_at.isoformat() if campaign.starts_at else None,
        "rules_version": campaign.rules_version,
        "catalog": reward_catalog(db),
        "gaps": reward_gaps(db),
    }


@router.post("/admin/adjust")
def admin_adjust(
    payload: AdjustIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    from app.domain.house_fidelity_admin import apply_manual_adjustment

    return apply_manual_adjustment(
        db,
        settings,
        account_id=payload.account_id,
        kind=payload.kind,
        reason=payload.reason,
        actor_ref=principal.actor_ref,
        credit_id=payload.credit_id,
    )
