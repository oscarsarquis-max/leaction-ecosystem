"""Motor de cálculo CRM — MRR, agregações e percentual de execução do contrato."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any


CONTRACT_STATUSES = frozenset({"ativo", "inadimplente", "cancelado", "trial"})
CONTRACT_ACCESS_ALLOWED = frozenset({"ativo", "trial"})
CONTRACT_ACCESS_BLOCKED = frozenset({"inadimplente", "cancelado"})
PLANO_PERIODICIDADES = frozenset({"Mensal", "Semestral", "Anual"})
PLANO_TIPOS = frozenset({"base", "addon"})


def _to_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def calc_percentual_execucao(
    data_inicio: date | datetime | str | None,
    data_vencimento: date | datetime | str | None,
    *,
    hoje: date | None = None,
) -> float | None:
    """((hoje - início) / (vencimento - início)) * 100. None se datas inválidas ou duração zero."""
    inicio = _to_date(data_inicio)
    fim = _to_date(data_vencimento)
    if inicio is None or fim is None:
        return None

    duracao = (fim - inicio).days
    if duracao <= 0:
        return None

    ref = hoje or date.today()
    decorrido = (ref - inicio).days
    pct = (decorrido / duracao) * 100.0
    return round(max(0.0, min(100.0, pct)), 2)


def _decimal_to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def serializar_contrato_dashboard(row: dict, *, hoje: date | None = None) -> dict:
    inicio = row.get("data_inicio")
    vencimento = row.get("data_vencimento")
    return {
        "id": row["id"],
        "id_clie": row["id_clie"],
        "nome_clie": row.get("nome_clie"),
        "mail_clie": row.get("mail_clie"),
        "id_plano": row["id_plano"],
        "nome_plano": row.get("nome_plano"),
        "valor_negociado": _decimal_to_float(row.get("valor_negociado")),
        "status": row.get("status"),
        "data_inicio": inicio.isoformat() if hasattr(inicio, "isoformat") else inicio,
        "data_vencimento": vencimento.isoformat() if hasattr(vencimento, "isoformat") else vencimento,
        "percentual_execucao": calc_percentual_execucao(inicio, vencimento, hoje=hoje),
    }


def montar_dashboard_payload(
    contratos_ativos: list[dict],
    receita_por_plano: list[dict],
    *,
    mrr_addons: float = 0.0,
) -> dict[str, Any]:
    hoje = date.today()
    contratos = [serializar_contrato_dashboard(r, hoje=hoje) for r in contratos_ativos]
    mrr_contratos = sum(c["valor_negociado"] for c in contratos)
    mrr_total = round(mrr_contratos + float(mrr_addons or 0), 2)

    por_plano = []
    for row in receita_por_plano:
        por_plano.append({
            "id_plano": row["id_plano"],
            "nome_plano": row.get("nome_plano"),
            "mrr": _decimal_to_float(row.get("mrr")),
            "contratos_ativos": int(row.get("contratos_ativos") or 0),
            "tipo_plano": row.get("tipo_plano") or "base",
        })

    return {
        "mrr_total": mrr_total,
        "mrr_contratos": round(mrr_contratos, 2),
        "mrr_addons": round(float(mrr_addons or 0), 2),
        "receita_por_plano": por_plano,
        "contratos_ativos": contratos,
    }


def is_contract_access_allowed(status: str | None) -> bool:
    """Sem contrato cadastrado → libera (clientes legados). Bloqueia inadimplente/cancelado."""
    if not status:
        return True
    normalized = str(status).strip().lower()
    if normalized in CONTRACT_ACCESS_BLOCKED:
        return False
    if normalized in CONTRACT_ACCESS_ALLOWED:
        return True
    return True


def parse_beneficios_input(raw: Any) -> list[str]:
    """Converte texto (\n ou ;) ou lista em array de benefícios."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, dict):
        items = raw.get("beneficios") or raw.get("items") or []
        if isinstance(items, list):
            return parse_beneficios_input(items)
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parse_beneficios_input(parsed)
        except (TypeError, json.JSONDecodeError):
            pass
    parts = re.split(r"[\n;]+", text)
    return [part.strip() for part in parts if part.strip()]


def beneficios_from_db(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return parse_beneficios_input(raw)
    if isinstance(raw, (dict,)):
        return parse_beneficios_input(raw)
    text = str(raw).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return parse_beneficios_input(parsed)
    except (TypeError, json.JSONDecodeError):
        return parse_beneficios_input(text)


def beneficios_to_jsonb(raw: Any) -> str:
    return json.dumps(parse_beneficios_input(raw), ensure_ascii=False)


def normalizar_periodicidade(raw: Any, *, default: str = "Mensal") -> str:
    value = (str(raw).strip() if raw is not None else "") or default
    if value not in PLANO_PERIODICIDADES:
        return default
    return value
