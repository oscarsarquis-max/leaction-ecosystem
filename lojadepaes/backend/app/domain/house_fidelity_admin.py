from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import bakery_now
from app.domain.capacity import utc_now
from app.domain.cpf import mask_cpf
from app.domain.errors import ConfirmationError, NotFoundError
from app.domain.house_fidelity import (
    campaign_is_publicly_active,
    current_campaign,
    cycle_of,
    real_balance,
)
from app.models.customers import CustomerAccount
from app.models.house_fidelity import (
    HouseFidelityAdjustment,
    HouseFidelityCredit,
    HouseFidelityEvent,
)


def _month_qualifies(session: Session, campaign_id, account_id, year: int, month: int) -> int:
    return len(
        list(
            session.scalars(
                select(HouseFidelityEvent).where(
                    HouseFidelityEvent.campaign_id == campaign_id,
                    HouseFidelityEvent.account_id == account_id,
                    HouseFidelityEvent.kind == "qualify",
                    HouseFidelityEvent.status == "applied",
                    HouseFidelityEvent.cycle_year == year,
                    HouseFidelityEvent.cycle_month == month,
                )
            )
        )
    )


def _credit_block_reason(status: str) -> str | None:
    if status == "available":
        return None
    if status == "used":
        return "Este crédito já foi usado e não volta para o saldo."
    if status == "reserved":
        return "Este crédito está reservado em um pedido e não pode ser revertido agora."
    return "Este crédito já foi revertido."


def _credits_by_status(session: Session, campaign_id, account_id) -> dict[str, int]:
    rows = list(
        session.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.campaign_id == campaign_id,
                HouseFidelityCredit.account_id == account_id,
            )
        )
    )
    counts = {"available": 0, "reserved": 0, "used": 0, "returned": 0}
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
    return counts


def list_participants(
    session: Session,
    settings: Settings,
    *,
    query: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    campaign = current_campaign(session)
    now = bakery_now(settings)
    year, month = cycle_of(settings, now)
    filters = []
    cleaned = query.strip()
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    cpf_query = len(digits) >= 11
    if cpf_query:
        return {
            "items": [],
            "page": max(1, page),
            "page_size": min(50, max(1, page_size)),
            "total": 0,
            "campaign_status": None if campaign is None else campaign.status,
            "campaign_active": campaign_is_publicly_active(settings, campaign),
            "starts_at": None
            if campaign is None or campaign.starts_at is None
            else campaign.starts_at.isoformat(),
            "rules_version": None if campaign is None else campaign.rules_version,
            "search_note": "Busque por nome ou e-mail. O CPF não entra na busca.",
        }
    if cleaned:
        like = f"%{cleaned}%"
        filters.append(
            or_(
                CustomerAccount.name.ilike(like),
                CustomerAccount.email.ilike(like),
            )
        )
    count_stmt = select(func.count()).select_from(CustomerAccount)
    stmt = select(CustomerAccount).order_by(CustomerAccount.created_at.desc())
    if filters:
        count_stmt = count_stmt.where(*filters)
        stmt = stmt.where(*filters)
    total = session.scalar(count_stmt) or 0
    page = max(1, page)
    page_size = min(50, max(1, page_size))
    accounts = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    items = []
    for account in accounts:
        qualifies = 0
        available = 0
        if campaign is not None:
            qualifies = _month_qualifies(session, campaign.id, account.id, year, month)
            available = _credits_by_status(session, campaign.id, account.id)["available"]
        items.append(
            {
                "id": str(account.id),
                "name": account.name,
                "email": account.email,
                "cpf_masked": mask_cpf(account.cpf_last2),
                "verified": account.email_verified_at is not None,
                "valid_orders": qualifies,
                "valid_orders_month": qualifies,
                "credits_available": available,
            }
        )
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "campaign_status": None if campaign is None else campaign.status,
        "campaign_active": campaign_is_publicly_active(settings, campaign),
        "starts_at": None
        if campaign is None or campaign.starts_at is None
        else campaign.starts_at.isoformat(),
        "rules_version": None if campaign is None else campaign.rules_version,
    }


def participant_detail(session: Session, settings: Settings, account_id: str) -> dict:
    campaign = current_campaign(session)
    account = session.get(CustomerAccount, UUID(account_id))
    if account is None:
        raise NotFoundError("participante não encontrado")
    now = bakery_now(settings)
    year, month = cycle_of(settings, now)
    qualifies = 0
    counts = {"available": 0, "reserved": 0, "used": 0, "returned": 0}
    credits = []
    history = []
    progress = None
    if campaign is not None:
        qualifies = _month_qualifies(session, campaign.id, account.id, year, month)
        counts = _credits_by_status(session, campaign.id, account.id)
        if account.email_verified_at is not None:
            progress = real_balance(session, settings, account.id, campaign)
        for credit in session.scalars(
            select(HouseFidelityCredit)
            .where(
                HouseFidelityCredit.campaign_id == campaign.id,
                HouseFidelityCredit.account_id == account.id,
            )
            .order_by(HouseFidelityCredit.created_at.desc())
        ):
            credits.append(
                {
                    "id": str(credit.id),
                    "status": credit.status,
                    "cycle_year": credit.cycle_year,
                    "cycle_month": credit.cycle_month,
                    "created_at": credit.created_at.isoformat() if credit.created_at else None,
                    "reversible": credit.status == "available",
                    "block_reason": _credit_block_reason(credit.status),
                }
            )
        for event in session.scalars(
            select(HouseFidelityEvent)
            .where(
                HouseFidelityEvent.campaign_id == campaign.id,
                HouseFidelityEvent.account_id == account.id,
            )
            .order_by(HouseFidelityEvent.created_at.desc())
        ):
            history.append(
                {
                    "id": str(event.id),
                    "kind": event.kind,
                    "status": event.status,
                    "reason": event.reason,
                    "actor_ref": event.actor_ref,
                    "at": event.created_at.isoformat() if event.created_at else None,
                }
            )
        for row in session.scalars(
            select(HouseFidelityAdjustment)
            .where(
                HouseFidelityAdjustment.campaign_id == campaign.id,
                HouseFidelityAdjustment.account_id == account.id,
            )
            .order_by(HouseFidelityAdjustment.created_at.desc())
        ):
            history.append(
                {
                    "id": str(row.id),
                    "kind": f"adjustment_{row.kind}",
                    "status": "recorded",
                    "reason": row.reason,
                    "actor_ref": row.actor_ref,
                    "at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        history.sort(key=lambda item: item.get("at") or "", reverse=True)
    return {
        "id": str(account.id),
        "name": account.name,
        "email": account.email,
        "cpf_masked": mask_cpf(account.cpf_last2),
        "verified": account.email_verified_at is not None,
        "valid_orders_month": qualifies,
        "credits": counts,
        "credits_available": counts["available"],
        "progress": progress,
        "credit_rows": credits,
        "history": history,
        "can_grant": account.email_verified_at is not None and campaign is not None,
        "grant_block_reason": None
        if account.email_verified_at is not None
        else "Só é possível conceder crédito a um cadastro com e-mail verificado.",
    }


def apply_manual_adjustment(
    session: Session,
    settings: Settings,
    *,
    account_id: str,
    kind: str,
    reason: str,
    actor_ref: str,
    credit_id: str | None = None,
) -> dict:
    cleaned = reason.strip()
    if len(cleaned) < 3:
        raise ConfirmationError("informe por que este ajuste está sendo feito")
    campaign = current_campaign(session)
    if campaign is None:
        raise ConfirmationError("campanha não encontrada")
    account = session.get(CustomerAccount, UUID(account_id))
    if account is None:
        raise NotFoundError("participante não encontrado")
    if account.email_verified_at is None:
        raise ConfirmationError("só é possível ajustar um participante com e-mail verificado")
    now = bakery_now(settings)
    if kind == "grant":
        event = HouseFidelityEvent(
            campaign_id=campaign.id,
            account_id=account.id,
            kind="manual_grant",
            status="applied",
            cycle_year=now.year,
            cycle_month=now.month,
            eligible_at=now,
            reason=cleaned,
            actor_ref=actor_ref,
        )
        session.add(event)
        session.flush()
        existing = list(
            session.scalars(
                select(HouseFidelityCredit).where(
                    HouseFidelityCredit.campaign_id == campaign.id,
                    HouseFidelityCredit.account_id == account.id,
                    HouseFidelityCredit.cycle_year == now.year,
                    HouseFidelityCredit.cycle_month == now.month,
                )
            )
        )
        session.add(
            HouseFidelityCredit(
                campaign_id=campaign.id,
                account_id=account.id,
                source_event_id=event.id,
                cycle_year=now.year,
                cycle_month=now.month,
                group_index=max([row.group_index for row in existing], default=-1) + 1,
                status="available",
            )
        )
        session.add(
            HouseFidelityAdjustment(
                campaign_id=campaign.id,
                account_id=account.id,
                kind="grant",
                reason=cleaned,
                actor_ref=actor_ref,
            )
        )
        session.flush()
        return {"ok": True, "kind": "grant"}
    if kind != "reverse":
        raise ConfirmationError("ajuste não reconhecido")
    if not credit_id:
        raise ConfirmationError("escolha o crédito que será revertido")
    credit = session.get(HouseFidelityCredit, UUID(credit_id))
    if credit is None or credit.account_id != account.id or credit.campaign_id != campaign.id:
        raise NotFoundError("crédito não encontrado")
    if credit.status == "used":
        raise ConfirmationError(
            "crédito já usado não volta para o saldo e não altera a cobrança do pedido"
        )
    if credit.status == "reserved":
        raise ConfirmationError("crédito reservado em um pedido não pode ser revertido agora")
    if credit.status != "available":
        raise ConfirmationError("este crédito não está disponível para reversão")
    event = HouseFidelityEvent(
        campaign_id=campaign.id,
        account_id=account.id,
        kind="manual_reverse",
        status="applied",
        cycle_year=credit.cycle_year,
        cycle_month=credit.cycle_month,
        eligible_at=utc_now(),
        reason=cleaned,
        actor_ref=actor_ref,
    )
    session.add(event)
    credit.status = "returned"
    session.add(
        HouseFidelityAdjustment(
            campaign_id=campaign.id,
            account_id=account.id,
            kind="reverse",
            reason=cleaned,
            actor_ref=actor_ref,
        )
    )
    session.flush()
    return {"ok": True, "kind": "reverse"}
