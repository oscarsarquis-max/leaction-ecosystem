"""Data operacional única para elegibilidade, FEFO e superfícies de estoque (R026-009).

Fuso padrão: America/Sao_Paulo (calendário civil local, alinhado a reporting/custos).
Em PANNE_ENV=demo usa PANNE_DEMO_ANCHOR_DATE (default = seed DEFAULT_ANCHOR).
Em qualquer outro ambiente a âncora é ignorada — nunca aplica demo em produção.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import Settings, get_settings
from app.seed import DEFAULT_ANCHOR

OPERATIONAL_TIMEZONE = "America/Sao_Paulo"
_DEMO_ENVS = frozenset({"demo"})


class OperationalDateError(ValueError):
    """Configuração de data operacional incoerente (apenas ambiente demo)."""


def _parse_iso_date(raw: str) -> date:
    value = raw.strip()
    if not value:
        raise ValueError("data vazia")
    return date.fromisoformat(value)


def inventory_operational_date(
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> date:
    """Fonte única de `as_of` para domínio de estoque.

    - demo: âncora configurada (default documentado 2026-08-24); relógio real irrelevante.
    - demais: data civil atual em America/Sao_Paulo.
    """
    cfg = settings or get_settings()
    env = (cfg.env or "").strip().lower()

    if env in _DEMO_ENVS:
        raw = (cfg.demo_anchor_date or "").strip() or DEFAULT_ANCHOR
        try:
            return _parse_iso_date(raw)
        except ValueError as exc:
            raise OperationalDateError(
                f"PANNE_DEMO_ANCHOR_DATE inválida no ambiente demo: {raw!r}"
            ) from exc

    zone = ZoneInfo(OPERATIONAL_TIMEZONE)
    moment = now if now is not None else datetime.now(tz=zone)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=zone)
    else:
        moment = moment.astimezone(zone)
    return moment.date()


def inventory_as_of_payload(*, settings: Settings | None = None, now: datetime | None = None) -> dict[str, str]:
    """Metadado explícito no contrato HTTP de listagens de estoque."""
    as_of = inventory_operational_date(settings=settings, now=now)
    return {"as_of": as_of.isoformat(), "timezone": OPERATIONAL_TIMEZONE}
