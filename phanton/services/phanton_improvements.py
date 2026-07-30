"""Persistência e decisão de propostas de melhoria no Phanton (pós-retorno)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from models import PhantonImprovementProposal  # noqa: E402
from services.retorno_dual_vision import (  # noqa: E402
    resolve_phanton_improvement_proposal,
)

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"


class PhantonImprovementError(Exception):
    """Erro de domínio das propostas de melhoria Phanton."""


def create_proposal_from_retorno(
    db_session: Session,
    *,
    source_run_id: UUID,
    substitute_run_id: UUID,
    full_retorno: str,
    use_llm_fallback: bool = True,
    resolved: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Cria proposta pendente se o retorno trouxer melhoria no Phanton."""
    data = resolved or resolve_phanton_improvement_proposal(
        full_retorno, use_llm_fallback=use_llm_fallback
    )
    if not data.get("has_proposal"):
        return None

    row = PhantonImprovementProposal(
        id=uuid4(),
        source_run_id=source_run_id,
        substitute_run_id=substitute_run_id,
        title=str(data.get("title") or "Melhoria proposta no Phanton")[:200],
        summary=str(data.get("summary") or "").strip(),
        items=list(data.get("items") or []),
        raw_section=(data.get("raw_section") or "")[:20000] or None,
        status=STATUS_PENDING,
        source=str(data.get("source") or "section"),
    )
    if not row.summary:
        return None

    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return proposal_to_dict(row)


def proposal_to_dict(row: PhantonImprovementProposal) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "source_run_id": str(row.source_run_id) if row.source_run_id else None,
        "substitute_run_id": (
            str(row.substitute_run_id) if row.substitute_run_id else None
        ),
        "title": row.title,
        "summary": row.summary,
        "items": row.items if isinstance(row.items, list) else [],
        "status": row.status,
        "source": row.source,
        "created_at": row.created_at,
        "decided_at": row.decided_at,
    }


def decide_proposal(
    db_session: Session,
    proposal_id: str | UUID,
    *,
    decision: str,
) -> dict[str, Any]:
    """Aceita ou rejeita explicitamente a melhoria proposta no Phanton."""
    decision_norm = (decision or "").strip().lower()
    if decision_norm in ("accept", "aceitar", "accepted"):
        next_status = STATUS_ACCEPTED
    elif decision_norm in ("reject", "rejeitar", "rejected"):
        next_status = STATUS_REJECTED
    else:
        raise PhantonImprovementError(
            "Decisão inválida — use aceitar ou rejeitar."
        )

    pid = proposal_id if isinstance(proposal_id, UUID) else UUID(str(proposal_id))
    row = db_session.get(PhantonImprovementProposal, pid)
    if row is None:
        raise PhantonImprovementError(f"Proposta não encontrada: {pid}")

    if row.status != STATUS_PENDING:
        raise PhantonImprovementError(
            f"Proposta já decidida (status={row.status})"
        )

    row.status = next_status
    row.decided_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(row)
    return proposal_to_dict(row)
