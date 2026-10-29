"""Manifesto e cobertura de tabelas. Ausências têm motivo."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.seed import ALEMBIC_HEAD, SCENARIO_VERSION

INTENTIONAL_EMPTY = {
    "bedrock_invocation": "Proibido neste ciclo. Somente FakeModelGateway.",
    "cms_remote_cache": "Editorial só no provider estático local.",
    "practiced_price_history": "Histórico extra não exigido além do preço vigente demo.",
}

JOURNEYS = [
    "aplicação: migrations, reference, /me, troca de organização",
    "ingrediente/receita: versão, publicação, formulação, escala",
    "produção: plano, ordem, pesagem, consumo, etapas, ficha",
    "conformidade/custos: dossiê, revisão, cálculo, simulação",
    "estoque/compras: lote, reserva, inventário, pedido",
    "relatórios/interface: visão salva, snapshot, quadro, assistente",
]


def table_counts(session: Session) -> dict[str, int]:
    inspector = inspect(session.get_bind())
    counts: dict[str, int] = {}
    for name in inspector.get_table_names():
        counts[name] = int(session.execute(text(f'SELECT count(*) FROM "{name}"')).scalar() or 0)
    return counts


def build_manifest(
    session: Session,
    *,
    anchor: date,
    gaps: list[str],
    elapsed_s: float,
    alembic_head: str | None,
) -> dict:
    counts = table_counts(session)
    empty = {name: counts[name] for name in counts if counts[name] == 0}
    digest = hashlib.sha256(json.dumps(counts, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "scenario_version": SCENARIO_VERSION,
        "alembic_head": alembic_head or ALEMBIC_HEAD,
        "anchor_date": anchor.isoformat(),
        "organizations": ["Panne Demonstração", "Padaria Horizonte Demo"],
        "journeys": JOURNEYS,
        "table_counts": counts,
        "empty_tables": empty,
        "intentional_empty": INTENTIONAL_EMPTY,
        "gaps": gaps,
        "hashes": {"table_counts": digest},
        "duration_seconds": round(elapsed_s, 3),
        "verification": "ok" if not [item for item in gaps if item.startswith("fatal")] else "falha",
    }


def write_manifest(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def coverage_report(payload: dict) -> str:
    lines = [
        f"# Cobertura do cenário {payload['scenario_version']}",
        "",
        f"- Alembic: `{payload['alembic_head']}`",
        f"- Data-âncora: {payload['anchor_date']}",
        f"- Duração: {payload['duration_seconds']}s",
        f"- Verificação: {payload['verification']}",
        "",
        "## Organizações",
        "",
    ]
    for name in payload["organizations"]:
        lines.append(f"- {name}")
    lines.extend(["", "## Jornadas", ""])
    for item in payload["journeys"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Contagem por tabela", ""])
    for name, count in sorted(payload["table_counts"].items()):
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", "## Tabelas vazias", ""])
    for name, count in sorted(payload["empty_tables"].items()):
        reason = payload["intentional_empty"].get(name, "Sem linha neste recorte; ausência legítima.")
        lines.append(f"- `{name}` ({count}): {reason}")
    if payload["gaps"]:
        lines.extend(["", "## Lacunas", ""])
        for gap in payload["gaps"]:
            lines.append(f"- {gap}")
    return "\n".join(lines) + "\n"
