"""
Farinha: preços append-only — não UPDATE.
Insere linhas normalizadas (×25) com mesma data/origem; o seletor usa
(observed_at, created_at, id) e passa a preferir as novas.

12,50→312,50 · 13,10→327,50 · 13,00→325,00
Somente panne_demo.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.costing_pricing.models import CostingPolicyVersion  # noqa: E402
from app.modules.costing_pricing.services import run_calculation  # noqa: E402
from app.modules.identity_organization.tenant_context import apply_tenant_context  # noqa: E402
from app.modules.ingredient_catalog.models import SupplierItem, SupplierItemPrice  # noqa: E402
from app.seed.demo import seed_identity  # noqa: E402
from app.seed.ids import at, seed_uuid  # noqa: E402

PAIRS = (
    (Decimal("12.50"), Decimal("312.50")),
    (Decimal("13.10"), Decimal("327.50")),
    (Decimal("13.00"), Decimal("325.00")),
)
DESC = (
    "Fundamento: PRECO DA EMBALAGEM INTEIRA (25 kg). "
    "Historicos 12,50/13,10/13,00 tinham magnitude de R$/kg sob contrato de embalagem; "
    "normalizados x25 para 312,50/327,50/325,00 (mesma data/origem, append-only). Sintetico."
)


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"))


def main() -> None:
    url = os.environ.get("PANNE_PATCH_URL") or ""
    if "/panne_demo" not in url:
        raise SystemExit("alvo deve ser panne_demo")
    engine = create_engine(url, future=True)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        world = seed_identity(session)
        apply_tenant_context(
            session, organization_id=world.organization.id, user_id=world.users["demo-owner"].id
        )
        item = session.scalar(
            select(SupplierItem).where(
                SupplierItem.organization_id == world.organization.id,
                SupplierItem.supplier_sku == "SKU-FAR-25",
            )
        )
        assert item is not None
        item.package_quantity = Decimal("25")
        item.description = DESC
        session.flush()

        existing = list(
            session.scalars(select(SupplierItemPrice).where(SupplierItemPrice.supplier_item_id == item.id))
        )
        for old_amt, new_amt in PAIRS:
            matches = [p for p in existing if _q(p.unit_price) == _q(old_amt)]
            already = any(_q(p.unit_price) == _q(new_amt) for p in existing)
            if already:
                print(f"ja normalizado {_q(new_amt)}")
                continue
            for old in matches:
                session.add(
                    SupplierItemPrice(
                        supplier_item_id=item.id,
                        unit_price=new_amt,
                        currency=old.currency,
                        observed_at=old.observed_at,
                        source=old.source,
                    )
                )
                print(f"append {old.unit_price} -> {new_amt} @ {old.observed_at} ({old.source})")
        session.flush()

        policy = session.scalar(
            select(CostingPolicyVersion)
            .where(
                CostingPolicyVersion.organization_id == world.organization.id,
                CostingPolicyVersion.status == "published",
            )
            .order_by(CostingPolicyVersion.created_at.desc())
        )
        owner = world.principals["demo-owner"]
        for code, key in (
            ("PAO-FR", "a-norm"),
            ("FOCACCIA", "d-norm"),
            ("BRIOCHE", "brio-norm"),
            ("PAO-INT", "b-norm"),
        ):
            row = session.execute(
                text(
                    """
                    SELECT fv.id AS version_id, sc.id AS scale_id
                    FROM formulation_version fv
                    JOIN formulation f ON f.id=fv.formulation_id
                    JOIN technical_product tp ON tp.id=f.technical_product_id
                    LEFT JOIN scale_calculation sc ON sc.formulation_version_id=fv.id
                    WHERE tp.code=:code AND fv.status='published'
                    ORDER BY fv.version_number DESC LIMIT 1
                    """
                ),
                {"code": code},
            ).mappings().first()
            if row is None:
                continue
            body = {
                "kind": "planned",
                "policy_version_id": str(policy.id),
                "valuation_at": at(date(2026, 8, 24)).isoformat(),
                "formulation_version_id": str(row["version_id"]),
            }
            if row["scale_id"]:
                body["scale_calculation_id"] = str(row["scale_id"])
            calc = run_calculation(
                session,
                owner,
                body,
                idempotency_key=seed_uuid("pass3", "calc", key, "v2", str(row["version_id"])),
            )
            print(f"{code} planned total={calc.total_amount} sellable={calc.sellable_unit_amount} id={calc.id}")

        oid = session.execute(
            text(
                """
                SELECT po.id FROM production_order po
                JOIN technical_product tp ON tp.id=po.technical_product_id
                WHERE tp.code='FOCACCIA' AND po.status='completed'
                ORDER BY po.created_at DESC LIMIT 1
                """
            )
        ).scalar()
        if oid:
            calc = run_calculation(
                session,
                owner,
                {
                    "kind": "actual",
                    "policy_version_id": str(policy.id),
                    "valuation_at": at(date(2026, 8, 24)).isoformat(),
                    "production_order_id": str(oid),
                },
                idempotency_key=seed_uuid("pass3", "calc", "d-actual-norm", "v2", str(oid)),
            )
            print(f"FOCACCIA actual total={calc.total_amount} sellable={calc.sellable_unit_amount} id={calc.id}")

        session.commit()
        print("OK normalize_flour_append")


if __name__ == "__main__":
    main()
