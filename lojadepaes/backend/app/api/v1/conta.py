from fastapi import APIRouter, Response

from app.api.deps import AppSettings, DbSession, OptionalCustomer
from app.domain.baker_library.access import access_for_account
from app.domain.house_fidelity import status_payload

router = APIRouter(prefix="/conta", tags=["conta"])


def account_situation(db, settings, account) -> dict:
    access = access_for_account(db, settings, account)
    fidelity = status_payload(db, settings, account=account)
    participant = fidelity.get("participant") if isinstance(fidelity, dict) else None
    bread_credits = 0
    stamps_label = None
    enrolled = False
    if isinstance(participant, dict):
        enrolled = True
        bread_credits = int(participant.get("credits") or 0)
        stamps_label = participant.get("progress_label")
    status = str(access.get("subscription_status") or ("unidentified" if account is None else "none"))
    labels = {
        "active": "Assinatura ativa",
        "pending": "Assinatura pendente",
        "cancelled_with_access": "Renovação cancelada · acesso vigente",
        "none": "Sem assinatura",
        "unidentified": "Identifique-se",
    }
    return {
        "identified": bool(account),
        "name": account.name if account is not None else None,
        "assinatura": {
            "label": "Assinatura",
            "status": "unidentified" if account is None else status,
            "status_label": labels["unidentified"] if account is None else labels.get(status, labels["none"]),
            "authorized": bool(access.get("authorized")),
            "subscriber_discount": bool(access.get("subscriber_discount")),
            "valid_until": access.get("valid_until"),
            "cancelable": bool(
                account is not None
                and (
                    status == "active"
                    or any(
                        isinstance(item, dict) and item.get("cancelable")
                        for item in (access.get("subscriptions") or [])
                    )
                )
            ),
            "cancel_policy": access.get("cancel_policy"),
        },
        "consultas_ia": {
            "label": "Consultas de IA",
            "credits": access.get("ai_credits") if account is not None else None,
            "monthly_credits": access.get("monthly_credits") if account is not None else None,
            "pack_credits": access.get("pack_credits") if account is not None else None,
            "pack_expires": False,
            "can_use_ai": bool(access.get("can_use_ai")),
            "balance_source": access.get("balance_source"),
        },
        "fidelidade": {
            "label": "Fidelidade / créditos de pão",
            "enrolled": enrolled,
            "campaign_active": bool(fidelity.get("campaign_active")),
            "bread_credits": bread_credits if enrolled else 0,
            "stamps_label": stamps_label,
        },
        "plans_href": access.get("plans_href") or (access.get("plan") or {}).get("plans_href"),
        "message": access.get("message"),
    }


@router.get("/situacao")
def conta_situacao(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    account: OptionalCustomer,
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return account_situation(db, settings, account)
