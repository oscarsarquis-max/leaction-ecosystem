"""Dry-run sem mutação. Plano em base vazia; inspeção em base populada."""

from __future__ import annotations

import hashlib
import json
from datetime import date

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.modules.identity_organization.models import Organization
from app.modules.inventory_procurement.models import InventoryPolicy, InventoryPolicyVersion
from app.seed import ALEMBIC_HEAD, SCENARIO_VERSION
from app.seed.demo import ORG_A
from app.seed.manifest import table_counts

PLANNED_EMPTY = [
    "aplicar catálogo de referência (unidades, nutrientes, alérgenos)",
    "criar duas organizações e os sete perfis demo",
    "publicar ingredientes e receitas do cenário",
    "avançar planos e ordens pelos estados operacionais",
    "abrir estoque, reservas, compras e inventário por comandos",
    "avaliar dossiês, custos e relatórios sintéticos",
    "registrar proposta de receita somente no gateway falso",
]

PLANNED_POPULATED = [
    "inspecionar organizações, perfis e âncora já persistidos",
    "reconciliar contagens com o cenário sem regravar",
    "listar o que um seed faria se a base estivesse vazia",
    "não republicar política, receita, dossiê nem preço",
    "não reliberar ordem, não reabrir inventário e não reemitir ficha",
]


def _digest(counts: dict[str, int]) -> str:
    return hashlib.sha256(json.dumps(counts, sort_keys=True).encode("utf-8")).hexdigest()


def inspect_dry_run(session: Session, *, anchor: date, target: dict[str, str]) -> dict:
    before = table_counts(session)
    inspector = inspect(session.get_bind())
    tables = set(inspector.get_table_names())
    org = None
    if "organization" in tables:
        org = session.scalar(select(Organization).where(Organization.slug == ORG_A))
    populated = org is not None
    impediments: list[str] = []
    if "alembic_version" not in tables:
        impediments.append("schema ausente; aplicar 0001→0020 antes do seed real")
    if populated:
        published = None
        if "inventory_policy_version" in tables:
            published = session.scalar(
                select(InventoryPolicyVersion).where(InventoryPolicyVersion.status == "published")
            )
        if published is not None:
            impediments.append(
                "política de estoque já publicada é imutável; dry-run não tenta republicar"
            )
        policy = None
        if "inventory_policy" in tables:
            policy = session.scalar(select(InventoryPolicy).where(InventoryPolicy.code == "EST-DEMO"))
        if policy is not None:
            impediments.append("comandos de liberação e divisão não são executados em base populada")
        planned = list(PLANNED_POPULATED)
        state = "populated"
    else:
        planned = list(PLANNED_EMPTY)
        state = "empty"
        if "organization" not in tables:
            impediments.append("pré-condição: banco isolado com Alembic 0020 aplicado")
    after = table_counts(session)
    mutated = before != after
    if mutated:
        impediments.append("falha interna: dry-run alterou contagens")
    return {
        "dry_run": True,
        "mutated": mutated,
        "target": {
            "database": target.get("database"),
            "host": target.get("host"),
            "port": target.get("port"),
            "env": target.get("env"),
        },
        "scenario": SCENARIO_VERSION,
        "alembic_head": ALEMBIC_HEAD,
        "anchor": anchor.isoformat(),
        "database_state": state,
        "planned_actions": planned,
        "impediments": impediments,
        "counts_before": before,
        "counts_after": after,
        "hashes": {"before": _digest(before), "after": _digest(after)},
    }
