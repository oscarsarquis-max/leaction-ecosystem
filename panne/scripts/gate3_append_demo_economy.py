"""
GATE3 — append-only econômico direcionado (somente panne_demo).

NÃO reexecuta populate_demo_economy completo.
NÃO altera preços históricos sem sale_basis.

Prova de unidade comercial (domínio, não assunção):
  Cálculos planned/actual usam sellable_quantity em peças
  (PAO-FR 60, PAO-INT 55, FOCACCIA 8/7, MANTEIGA 1) e
  sellable_unit_amount = total ÷ sellable_quantity.
  Portanto a base comercial de venda é 1 × unidade (`un`), alinhada a
  technical_product.sale_unit_id = un.

Cenários (preço novo vigente, âncora +1 dia):
  A PAO-FR     custo 0,456647/un · preço 1,20/un · markup≈2,628 · margem≈62,0%
  B PAO-INT    custo parcial 0,104109/un · preço 1,10/un · comparação allowed
               com reason=cost_partial (margem NÃO definitiva)
  C MANTEIGA   custo 18,00/un · preço 24,90/un · markup≈1,383 · margem≈27,7%
  D FOCACCIA   custo planned 3,155150/un · preço 21,00/un · markup≈6,656
               (previsto 8 × realizado 7 preservado nos cálculos)

Políticas:
  org markup_factor 2,5
  família Pães markup_factor 2,8 (PAO-FR/PAO-INT)
  produto MANTEIGA margin_rate 0,25

Uso:
  $env:PANNE_PATCH_URL='postgresql+psycopg://…@127.0.0.1:5433/panne_demo'
  python scripts/gate3_append_demo_economy.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.costing_pricing.services import (  # noqa: E402
    activate_markup_policy,
    create_markup_policy,
    create_practiced_price,
    decide_price,
)
from app.modules.formula_lab.models import TechnicalProduct  # noqa: E402
from app.modules.identity_organization.tenant_context import apply_tenant_context  # noqa: E402
from app.modules.ingredient_catalog.models import MeasurementUnit  # noqa: E402
from app.modules.product_catalog.commands import create_family, update_product  # noqa: E402
from app.seed.demo import seed_identity  # noqa: E402
from app.seed.ids import at, seed_uuid  # noqa: E402

ANCHOR = date(2026, 8, 24)
SCRIPT_TAG = "gate3_append_demo_economy_v1"
EVIDENCE = ROOT / "documentacao" / "evidencias" / "cursor-028-custos-organic" / "gate3"


@dataclass
class Log:
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


SCENARIOS = {
    "PAO-FR": {
        "amount": "1.20",
        "basis_qty": "1",
        "note": "GATE3 A — preço por unidade vendável (sellable_quantity=60)",
        "expected_cost": "0.456647",
        "expected_markup": "2.628",
    },
    "PAO-INT": {
        "amount": "1.10",
        "basis_qty": "1",
        "note": "GATE3 B — preço com custo parcial; margem indicativa",
        "expected_cost": "0.104109",
        "expected_partial": True,
    },
    "MANTEIGA-PT": {
        "amount": "24.90",
        "basis_qty": "1",
        "note": "GATE3 C — tablete/unidade de aquisição e venda",
        "expected_cost": "18.000000",
        "expected_markup": "1.383",
    },
    "FOCACCIA": {
        "amount": "21.00",
        "basis_qty": "1",
        "note": "GATE3 D — preço por focaccia (unidade); previsto 8 / realizado 7 intactos",
        "expected_cost": "3.155150",
        "expected_markup": "6.656",
    },
}


def _url() -> str:
    raw = os.environ.get("PANNE_PATCH_URL") or os.environ.get("PANNE_DATABASE_URL")
    if not raw:
        raise SystemExit("Defina PANNE_PATCH_URL apontando para panne_demo")
    if "postgresql+asyncpg://" in raw:
        raw = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if "/panne_demo" not in raw and not raw.rstrip("/").endswith("panne_demo"):
        raise SystemExit("Recusado: alvo deve ser logical database panne_demo")
    if "/panne?" in raw or raw.rstrip("/").endswith("/panne"):
        raise SystemExit("Recusado: banco panne (produção) é proibido")
    return raw


def _unit(session: Session, code: str) -> MeasurementUnit:
    row = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == code))
    if row is None:
        raise SystemExit(f"unidade {code} ausente")
    return row


def _product(session: Session, org_id, code: str) -> TechnicalProduct | None:
    return session.scalar(
        select(TechnicalProduct).where(
            TechnicalProduct.organization_id == org_id, TechnicalProduct.code == code
        )
    )


def ensure_sale_units_and_family(session: Session, world, log: Log) -> dict:
    owner = world.principals["demo-owner"]
    org_id = world.organization.id
    un = _unit(session, "un")
    family = session.execute(
        text("select id from product_family where organization_id=:o and code='PAES'"),
        {"o": org_id},
    ).scalar()
    if family is None:
        fam = create_family(
            session,
            owner,
            code="PAES",
            display_name="Pães",
        )
        family = fam.id
        log.added.append("família PAES")
    else:
        log.skipped.append("família PAES")

    mapping = {}
    for code in SCENARIOS:
        product = _product(session, org_id, code)
        if product is None:
            log.skipped.append(f"produto ausente {code}")
            continue
        fields: dict = {}
        if product.sale_unit_id is None:
            fields["sale_unit_id"] = un.id
        if code in {"PAO-FR", "PAO-INT"} and product.family_id is None:
            fields["family_id"] = family
        if fields:
            update_product(
                session,
                owner,
                product_id=product.id,
                expected_row_version=product.row_version,
                **fields,
            )
            log.added.append(f"produto {code} sale_unit/family {list(fields)}")
        else:
            log.skipped.append(f"produto {code} já configurado")
        session.refresh(product)
        mapping[code] = product
    return mapping


def ensure_policies(session: Session, world, products: dict, log: Log) -> None:
    owner = world.principals["demo-owner"]
    org_id = world.organization.id
    valid_from = at(ANCHOR, days=-90).isoformat()

    specs = [
        {
            "key": "pol-org",
            "body": {
                "code": "ORG-MK-25",
                "display_name": "Markup organização 2,5×",
                "kind": "markup_factor",
                "value": "2.5",
                "scope_level": "organization",
                "valid_from": valid_from,
                "justification": f"{SCRIPT_TAG} política organização",
            },
        },
    ]
    paes = session.execute(
        text("select id from product_family where organization_id=:o and code='PAES'"),
        {"o": org_id},
    ).scalar()
    if paes:
        specs.append(
            {
                "key": "pol-family",
                "body": {
                    "code": "FAM-PAES-MK-28",
                    "display_name": "Markup família Pães 2,8×",
                    "kind": "markup_factor",
                    "value": "2.8",
                    "scope_level": "family",
                    "product_family_id": str(paes),
                    "valid_from": valid_from,
                    "justification": f"{SCRIPT_TAG} política família",
                },
            }
        )
    manteiga = products.get("MANTEIGA-PT")
    if manteiga:
        specs.append(
            {
                "key": "pol-product",
                "body": {
                    "code": "PROD-MANTEIGA-MG-25",
                    "display_name": "Margem manteiga 25%",
                    "kind": "margin_rate",
                    "value": "0.25",
                    "scope_level": "product",
                    "technical_product_id": str(manteiga.id),
                    "valid_from": valid_from,
                    "justification": f"{SCRIPT_TAG} política produto",
                },
            }
        )

    for spec in specs:
        data = create_markup_policy(
            session, owner, spec["body"], idempotency_key=seed_uuid("gate3", "pol", spec["key"])
        )
        if data.get("status") == "draft":
            activate_markup_policy(
                session,
                owner,
                data["id"],
                expected_version=data.get("row_version"),
                idempotency_key=seed_uuid("gate3", "polact", spec["key"]),
                notes="ativação demonstração GATE3",
            )
            log.added.append(f"política {spec['body']['code']} active")
        else:
            log.skipped.append(f"política {spec['body']['code']} replay")


def ensure_new_prices(session: Session, world, products: dict, log: Log) -> None:
    owner = world.principals["demo-owner"]
    un = _unit(session, "un")
    valid_from = at(ANCHOR, days=1)  # after legacy ladder; append-only succession
    for code, spec in SCENARIOS.items():
        product = products.get(code)
        if product is None or product.sale_unit_id is None:
            log.skipped.append(f"preço {code}: sale_unit ausente")
            continue
        body = {
            "technical_product_id": str(product.id),
            "channel": "own_counter",
            "amount": spec["amount"],
            "currency": "BRL",
            "valid_from": valid_from.isoformat(),
            "justification": spec["note"],
            "sale_basis_quantity": spec["basis_qty"],
            "sale_basis_unit_id": str(un.id),
        }
        price = create_practiced_price(
            session, owner, body, idempotency_key=seed_uuid("gate3", "price", code)
        )
        if price.status == "draft":
            decide_price(
                session,
                owner,
                price.id,
                {
                    "decision": "publish",
                    "notes": "aplicação demonstração GATE3",
                    "reinforced_confirmation": True,
                },
                expected_version=price.row_version,
                idempotency_key=seed_uuid("gate3", "pricepub", code),
            )
            log.added.append(f"preço vigente {code} {spec['amount']} / 1 un")
        else:
            log.skipped.append(f"preço {code} replay status={price.status}")


def main() -> None:
    engine = create_engine(_url(), future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    log = Log()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session:
        world = seed_identity(session)
        apply_tenant_context(
            session,
            organization_id=world.organization.id,
            user_id=world.users["demo-owner"].id,
            issuer="gate3",
            subject="append",
        )
        before = session.execute(
            text(
                """
                select tp.code, pp.amount::text, pp.status, pp.sale_basis_quantity::text,
                       pp.valid_from::text
                from practiced_price pp
                join technical_product tp on tp.id=pp.technical_product_id
                where tp.code in ('PAO-FR','PAO-INT','MANTEIGA-PT','FOCACCIA')
                order by tp.code, pp.valid_from
                """
            )
        ).mappings().all()
        (EVIDENCE / "prices-before.json").write_text(
            json.dumps([dict(r) for r in before], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        products = ensure_sale_units_and_family(session, world, log)
        ensure_policies(session, world, products, log)
        ensure_new_prices(session, world, products, log)
        session.commit()
        after = session.execute(
            text(
                """
                select tp.code, pp.amount::text, pp.status, pp.sale_basis_quantity::text,
                       mu.code as unit, pp.valid_from::text, pp.valid_to::text, pp.justification
                from practiced_price pp
                join technical_product tp on tp.id=pp.technical_product_id
                left join measurement_unit mu on mu.id=pp.sale_basis_unit_id
                where tp.code in ('PAO-FR','PAO-INT','MANTEIGA-PT','FOCACCIA')
                order by tp.code, pp.valid_from
                """
            )
        ).mappings().all()
        (EVIDENCE / "prices-after.json").write_text(
            json.dumps([dict(r) for r in after], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        policies = session.execute(
            text(
                "select code, kind, value::text, scope_level, status from pricing_markup_policy order by code"
            )
        ).mappings().all()
        (EVIDENCE / "policies.json").write_text(
            json.dumps([dict(r) for r in policies], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (EVIDENCE / "SCENARIOS.json").write_text(
            json.dumps({"tag": SCRIPT_TAG, "scenarios": SCENARIOS, "log": log.__dict__}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(json.dumps(log.__dict__, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
