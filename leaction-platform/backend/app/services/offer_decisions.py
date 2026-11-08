"""Exceções humanas de aceite/rejeição, auditáveis e por perfil."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_decisions(origin: str, category: str) -> dict[str, dict[str, Any]]:
    from app.database import DB_AVAILABLE, db
    from app.database.models import MarketplaceOfferDecision

    if not DB_AVAILABLE or db is None or MarketplaceOfferDecision is None:
        return {}
    try:
        rows = (
            db.session.execute(
                db.select(MarketplaceOfferDecision).where(
                    MarketplaceOfferDecision.origin == origin,
                    MarketplaceOfferDecision.category == category,
                )
            )
            .scalars()
            .all()
        )
    except Exception as exc:
        logger.warning("Decisões editoriais indisponíveis (%s)", exc)
        return {}
    return {
        f"{row.origin}|{row.category}|{row.offer_id}": {
            "decision": row.decision,
            "reason": row.reason,
        }
        for row in rows
    }


def upsert_decision(
    *,
    offer_id: str,
    origin: str,
    category: str,
    decision: str,
    reason: str,
) -> dict[str, Any]:
    from app.database import DB_AVAILABLE, db
    from app.database.models import MarketplaceOfferDecision

    if not DB_AVAILABLE or db is None or MarketplaceOfferDecision is None:
        raise RuntimeError("Banco indisponível para decisão editorial.")
    row = db.session.get(MarketplaceOfferDecision, (offer_id, origin, category))
    if row is None:
        row = MarketplaceOfferDecision(
            offer_id=offer_id,
            origin=origin,
            category=category,
            decision=decision,
            reason=reason,
        )
        db.session.add(row)
    else:
        row.decision = decision
        row.reason = reason
    db.session.commit()
    return row.to_dict()
