"""
População econômica incremental — somente panne_demo.

Cenários canônicos:
  A PAO-FR     custo completo + rendimento + embalagem + histórico
  B PAO-INT    incompleto intencional (FAR-INT sem preço)
  C MANTEIGA-PT produto comprado (sem OP)
  D FOCACCIA   variação previsto×realizado + good_units
  E política família/produto → documentado como futuro (contrato ainda sem precedência)

Uso:
  $env:PANNE_PATCH_URL='postgresql+psycopg://admin:password123@127.0.0.1:5433/panne_demo'
  python scripts/populate_demo_economy.py

Idempotente. Origem dos preços sintéticos: demonstração.
Não toca no banco panne. Sem truncate/reseed.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.costing_pricing.models import CostingPolicyVersion  # noqa: E402
from app.modules.costing_pricing.services import (  # noqa: E402
    create_practiced_price,
    decide_price,
    run_calculation,
)
from app.modules.formula_lab.models import (  # noqa: E402
    Formulation,
    FormulationItem,
    FormulationVersion,
    ScaleCalculation,
)
from app.modules.identity_organization.models import Organization  # noqa: E402
from app.modules.identity_organization.tenant_context import apply_tenant_context  # noqa: E402
from app.modules.ingredient_catalog.models import (  # noqa: E402
    Ingredient,
    IngredientVersion,
    MeasurementUnit,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.production_execution.constants import YIELD_GOOD_UNITS  # noqa: E402
from app.modules.production_execution.yields import record_yield  # noqa: E402
from app.modules.production_planning.models import ProductionBatch, ProductionOrder  # noqa: E402
from app.seed.demo import _advance_production, seed_identity, seed_ingredients  # noqa: E402
from app.seed.ids import at, seed_uuid  # noqa: E402
from tests import helpers  # noqa: E402

ANCHOR = date(2026, 8, 24)
VALUATION = at(ANCHOR)
EVIDENCE_DIR = ROOT / "documentacao" / "evidencias" / "cursor-028-economia-demo"
SCRIPT_TAG = "populate_demo_economy_v1"


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


@dataclass
class ChangeLog:
    corrected: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# code, supplier, name, sku, pkg_qty, unit, prices[(days_before_anchor, amount)], basis_note
PRICE_SPECS: tuple = (
    ("AGUA", "FOR-UTIL", "Utilidades Demo", "SKU-AGUA-20", Decimal("20000"), "g",
     ((-30, "7.50"), (-14, "7.80"), (-1, "8.00")), "preço da embalagem 20 kg"),
    ("SAL", "FOR-SECO", "Secos Demo", "SKU-SAL-1", Decimal("1000"), "g",
     ((-30, "4.20"), (-14, "4.35"), (-1, "4.50")), "preço da embalagem 1 kg"),
    ("FER-BIO", "FOR-FERM", "Fermento Demo", "SKU-FER-500", Decimal("500"), "g",
     ((-30, "16.50"), (-14, "17.20"), (-1, "18.00")), "preço da embalagem 500 g"),
    ("ACUCAR", "FOR-SECO", "Secos Demo", "SKU-ACU-1", Decimal("1000"), "g",
     ((-30, "5.40"), (-14, "5.70"), (-1, "5.90")), "preço da embalagem 1 kg"),
    ("OLEO", "FOR-UTIL", "Utilidades Demo", "SKU-OLEO-900", Decimal("900"), "g",
     ((-30, "6.90"), (-14, "7.20"), (-1, "7.50")), "preço da embalagem 900 g"),
    ("MANTEIGA", "FOR-LATIC", "Laticínio Demo", "SKU-MAN-500", Decimal("500"), "g",
     ((-30, "16.00"), (-14, "17.00"), (-1, "18.00")), "preço da embalagem 500 g"),
    ("MARGARINA", "FOR-LATIC", "Laticínio Demo", "SKU-MARG-500", Decimal("500"), "g",
     ((-30, "8.00"), (-14, "8.50"), (-1, "9.00")), "preço da embalagem 500 g"),
    ("LEITE", "FOR-LATIC", "Laticínio Demo", "SKU-LEI-1", Decimal("1000"), "g",
     ((-30, "11.80"), (-14, "12.50"), (-1, "13.10")), "preço da embalagem 1 L equiv. 1000 g"),
    ("OVO", "FOR-GRANJA", "Granja Demo", "SKU-OVO-30", Decimal("1800"), "g",
     ((-30, "11.80"), (-14, "12.50"), (-1, "13.10")), "preço da embalagem ~30 ovos / 1800 g"),
    ("EMB-PAPEL", "FOR-EMB", "Embalagens Demo", "SKU-EMB-1000", Decimal("1000"), "g",
     ((-30, "10.00"), (-14, "11.00"), (-1, "12.00")), "preço da embalagem 1000 g papel (≈100 sacos)"),
    ("CHOCOLATE", "FOR-SECO", "Secos Demo", "SKU-CHOC-1", Decimal("1000"), "g",
     ((-30, "28.00"), (-14, "29.50"), (-1, "31.00")), "preço da embalagem 1 kg"),
    ("MORANGO", "FOR-HORTI", "Hortifruti Demo", "SKU-MOR-1", Decimal("1000"), "g",
     ((-30, "12.00"), (-14, "13.00"), (-1, "14.00")), "preço da embalagem 1 kg"),
)

# FAR-INT e GERGELIM ficam sem preço de propósito (cenário B / catálogo incompleto).
INTENTIONAL_GAPS = ("FAR-INT", "GERGELIM")

YIELDS = {
    "PAO-FR": (60, Decimal("50"), Decimal("0.10")),
    "PAO-INT": (55, Decimal("50"), Decimal("0.10")),
    "FOCACCIA": (8, Decimal("400"), Decimal("0.08")),
    "BRIOCHE": (20, Decimal("80"), Decimal("0.12")),
    "MANTEIGA-PT": (1, None, None),
}


def photograph(session: Session) -> dict:
    rows = session.execute(
        text(
            """
            SELECT o.slug,
              (SELECT count(*) FROM technical_product tp WHERE tp.organization_id=o.id) AS produtos,
              (SELECT count(*) FROM ingredient i WHERE i.organization_id=o.id) AS ingredientes,
              (SELECT count(*) FROM supplier s WHERE s.organization_id=o.id) AS fornecedores,
              (SELECT count(*) FROM supplier_item si WHERE si.organization_id=o.id) AS skus,
              (SELECT count(*) FROM supplier_item_price sip
                 JOIN supplier_item si ON si.id=sip.supplier_item_id
                WHERE si.organization_id=o.id) AS precos_compra,
              (SELECT count(*) FROM formulation f WHERE f.organization_id=o.id) AS receitas,
              (SELECT count(*) FROM production_order po WHERE po.organization_id=o.id) AS ordens,
              (SELECT count(*) FROM costing_calculation cc WHERE cc.organization_id=o.id) AS calculos,
              (SELECT count(*) FROM practiced_price pp WHERE pp.organization_id=o.id) AS precos_venda
            FROM organization o ORDER BY slug
            """
        )
    ).mappings().all()
    prices = session.execute(
        text(
            """
            SELECT i.code, si.supplier_sku, si.package_quantity, mu.code AS unit,
                   sip.unit_price::text, sip.observed_at::date::text AS obs, sip.source
            FROM supplier_item_price sip
            JOIN supplier_item si ON si.id=sip.supplier_item_id
            JOIN ingredient i ON i.id=si.ingredient_id
            JOIN measurement_unit mu ON mu.id=si.measurement_unit_id
            JOIN organization o ON o.id=si.organization_id
            WHERE o.slug='panne-demonstracao'
            ORDER BY i.code, sip.observed_at
            """
        )
    ).mappings().all()
    yields = session.execute(
        text(
            """
            SELECT tp.code, fv.yield_units, fv.target_unit_weight_g::text,
                   fv.expected_bake_loss_rate::text
            FROM formulation_version fv
            JOIN formulation f ON f.id=fv.formulation_id
            JOIN technical_product tp ON tp.id=f.technical_product_id
            WHERE fv.version_number=1
            ORDER BY tp.code
            """
        )
    ).mappings().all()
    calcs = session.execute(
        text(
            """
            SELECT cc.id::text, cc.kind, cc.completeness, cc.total_amount::text,
                   cc.sellable_unit_amount::text, cc.sellable_quantity::text, tp.code
            FROM costing_calculation cc
            LEFT JOIN technical_product tp ON tp.id=cc.technical_product_id
            ORDER BY cc.created_at
            """
        )
    ).mappings().all()
    return {
        "counts": [dict(r) for r in rows],
        "prices": [dict(r) for r in prices],
        "yields": [dict(r) for r in yields],
        "calculations": [dict(r) for r in calcs],
    }


def _set_tenant(session: Session, org_id: UUID, user_id: UUID) -> None:
    apply_tenant_context(session, organization_id=org_id, user_id=user_id, issuer="demo-economy", subject="economy")


def _unit(session: Session, code: str) -> MeasurementUnit:
    row = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == code))
    if row is None:
        raise SystemExit(f"unidade {code} ausente")
    return row


def _ensure_ingredient(session: Session, org_id: UUID, code: str, name: str, log: ChangeLog) -> Ingredient:
    row = session.scalar(select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.code == code))
    if row is None:
        row = Ingredient(
            organization_id=org_id,
            code=code,
            display_name=name,
            ingredient_type="simple",
            status="active",
        )
        session.add(row)
        session.flush()
        gram = _unit(session, "g")
        session.add(
            IngredientVersion(
                ingredient_id=row.id,
                organization_id=org_id,
                version_number=1,
                status="published",
                nutrition_basis_type="per_100g",
                nutrition_basis_quantity=Decimal("100"),
                nutrition_basis_unit_id=gram.id,
            )
        )
        session.flush()
        log.added.append(f"ingrediente {code}")
        _ = gram
    return row


def ensure_prices(session: Session, org_id: UUID, log: ChangeLog) -> None:
    # Farinha: preservar histórico; só garantir package_quantity=25 kg.
    updated = session.execute(
        text(
            """
            UPDATE supplier_item si
            SET package_quantity = 25
            FROM measurement_unit mu
            WHERE si.supplier_sku = 'SKU-FAR-25'
              AND si.organization_id = :org
              AND si.measurement_unit_id = mu.id
              AND mu.code = 'kg'
              AND si.package_quantity <> 25
            RETURNING si.id
            """
        ),
        {"org": org_id},
    ).all()
    if updated:
        log.corrected.append("SKU-FAR-25 package_quantity → 25 kg (fundamento: preço da embalagem)")
    log.notes.append(
        "Farinha: unit_price = preço da embalagem 25 kg. "
        "R$ 12,50 (14/08) e R$ 13,10 (23/08) seed-demo; R$ 13,00 (24/08 23:03) receipt posterior à valuation 12:00."
    )
    log.notes.append(f"Lacunas intencionais sem preço: {', '.join(INTENTIONAL_GAPS)}")

    for code, sup_code, sup_name, sku, qty, unit_code, points, basis in PRICE_SPECS:
        if code in ("EMB-PAPEL", "CHOCOLATE", "MORANGO"):
            names = {
                "EMB-PAPEL": "Saco de papel pão (Demo)",
                "CHOCOLATE": "Chocolate em pó (Demo)",
                "MORANGO": "Morango (Demo)",
            }
            ingredient = _ensure_ingredient(session, org_id, code, names[code], log)
        else:
            ingredient = session.scalar(
                select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.code == code)
            )
            if ingredient is None:
                log.skipped.append(f"preço: ingrediente {code} ausente")
                continue
        unit = _unit(session, unit_code)
        supplier = session.scalar(
            select(Supplier).where(Supplier.organization_id == org_id, Supplier.code == sup_code)
        )
        if supplier is None:
            supplier = Supplier(organization_id=org_id, code=sup_code, display_name=sup_name, status="active")
            session.add(supplier)
            session.flush()
            log.added.append(f"fornecedor {sup_code}")
        item = session.scalar(
            select(SupplierItem).where(SupplierItem.organization_id == org_id, SupplierItem.supplier_sku == sku)
        )
        desc = f"Embalagem de demonstração · fundamento: {basis}"
        if item is None:
            item = SupplierItem(
                organization_id=org_id,
                supplier_id=supplier.id,
                ingredient_id=ingredient.id,
                supplier_sku=sku,
                description=desc,
                package_quantity=qty,
                measurement_unit_id=unit.id,
                status="active",
            )
            session.add(item)
            session.flush()
            log.added.append(f"SKU {sku}")
        else:
            item.package_quantity = qty
            item.measurement_unit_id = unit.id
            item.description = desc
        for days, amount in points:
            observed = at(ANCHOR, days=days)
            exists = session.scalar(
                select(SupplierItemPrice).where(
                    SupplierItemPrice.supplier_item_id == item.id,
                    SupplierItemPrice.observed_at == observed,
                    SupplierItemPrice.source == "demonstração",
                )
            )
            if exists is None:
                # Evita duplicar se já há preço seed no mesmo instante com outra origem.
                same_moment = session.scalar(
                    select(SupplierItemPrice).where(
                        SupplierItemPrice.supplier_item_id == item.id,
                        SupplierItemPrice.observed_at == observed,
                    )
                )
                if same_moment is not None:
                    log.skipped.append(f"preço {sku} @ {observed.date()} já existe ({same_moment.source})")
                    continue
                session.add(
                    SupplierItemPrice(
                        supplier_item_id=item.id,
                        unit_price=Decimal(amount),
                        currency="BRL",
                        observed_at=observed,
                        source="demonstração",
                    )
                )
                log.added.append(f"preço {sku} {amount} BRL @ {observed.date()} ({basis})")
            else:
                log.skipped.append(f"preço {sku} @ {observed.date()} já demonstração")


def _latest_published_fv(session: Session, org_id: UUID, code: str):
    return session.execute(
        text(
            """
            SELECT fv.id, fv.version_number, fv.yield_units, fv.target_unit_weight_g,
                   fv.expected_bake_loss_rate, f.id AS formulation_id
            FROM formulation_version fv
            JOIN formulation f ON f.id = fv.formulation_id
            JOIN technical_product tp ON tp.id = f.technical_product_id
            WHERE tp.organization_id = :org AND tp.code = :code AND fv.status = 'published'
            ORDER BY fv.version_number DESC
            LIMIT 1
            """
        ),
        {"org": org_id, "code": code},
    ).mappings().first()


def ensure_commercial_versions(session: Session, world, log: ChangeLog) -> None:
    """Cria vN+1 com rendimento (e embalagem no PAO-FR). Published está congelado."""
    from app.modules.calculation_engine.scale import calculate_total_dough_mass, persist_scale_calculation
    from app.modules.formula_lab.commands import publish_version, retire_version

    org_id = world.organization.id
    actor = world.users["demo-formulator"]
    principal = world.principals["demo-formulator"]
    emb_iv = None
    emb = session.scalar(select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.code == "EMB-PAPEL"))
    if emb is not None:
        emb_iv = session.scalar(
            select(IngredientVersion).where(
                IngredientVersion.ingredient_id == emb.id, IngredientVersion.version_number == 1
            )
        )

    for code, (units, weight, loss) in YIELDS.items():
        if code == "MANTEIGA-PT":
            continue
        current = _latest_published_fv(session, org_id, code)
        if current is None:
            log.skipped.append(f"yield: {code} sem versão publicada")
            continue
        same = (
            current["yield_units"] == units
            and (weight is None or current["target_unit_weight_g"] == weight)
            and (loss is None or current["expected_bake_loss_rate"] == loss)
        )
        if same:
            log.skipped.append(f"rendimento {code} já ok")
            continue

        old = session.get(FormulationVersion, current["id"])
        assert old is not None
        new_number = int(current["version_number"]) + 1
        # Idempotência: se já existe draft eco com esse número, reutilizar
        existing_draft = session.scalar(
            select(FormulationVersion).where(
                FormulationVersion.formulation_id == current["formulation_id"],
                FormulationVersion.version_number == new_number,
            )
        )
        if existing_draft is not None and existing_draft.status == "published":
            log.skipped.append(f"{code} v{new_number} já publicada")
            continue
        if existing_draft is None:
            new = FormulationVersion(
                id=seed_uuid("eco", "fv", code, str(new_number)),
                organization_id=org_id,
                formulation_id=current["formulation_id"],
                version_number=new_number,
                status="draft",
                yield_units=units,
                target_unit_weight_g=weight,
                expected_bake_loss_rate=loss,
                notes=f"{SCRIPT_TAG} rendimento comercial",
                created_by_user_id=actor.id,
            )
            session.add(new)
            session.flush()
            old_items = list(
                session.scalars(
                    select(FormulationItem)
                    .where(FormulationItem.formulation_version_id == old.id)
                    .order_by(FormulationItem.sequence)
                )
            )
            for item in old_items:
                session.add(
                    FormulationItem(
                        organization_id=org_id,
                        formulation_version_id=new.id,
                        ingredient_version_id=item.ingredient_version_id,
                        sequence=item.sequence,
                        net_quantity=item.net_quantity,
                        measurement_unit_id=item.measurement_unit_id,
                        correction_factor=item.correction_factor,
                        is_flour_basis=item.is_flour_basis,
                        role=item.role,
                        notes=item.notes,
                    )
                )
            if code == "PAO-FR" and emb_iv is not None:
                # Embalagem NÃO entra na formulação: escala de massa distorce o papel.
                # Schema legado também não aceita role=packaging. Documentado em evidências.
                pass
            session.flush()
            log.added.append(f"{code} v{new_number} draft com rendimento")
        else:
            new = existing_draft
            new.yield_units = units
            new.target_unit_weight_g = weight
            new.expected_bake_loss_rate = loss
            session.flush()

        helpers.approve_version(session, new, actor, "approved")
        session.flush()
        if old.status == "published":
            retire_version(
                session,
                principal,
                old.id,
                expected_version=None,
                idempotency_key=seed_uuid("eco", "retire", code, str(old.version_number)),
            )
            session.flush()
        publish_version(
            session,
            principal,
            new.id,
            expected_version=None,
            idempotency_key=seed_uuid("eco", "pub", code, str(new_number)),
        )
        session.flush()
        # Escala 3300 g na nova versão
        items = list(
            session.scalars(select(FormulationItem).where(FormulationItem.formulation_version_id == new.id))
        )
        scale = session.scalar(select(ScaleCalculation).where(ScaleCalculation.formulation_version_id == new.id))
        if scale is None:
            persist_scale_calculation(
                session, new, calculate_total_dough_mass(items, Decimal("3300")), actor.id
            )
            log.added.append(f"escala 3300 g {code} v{new_number}")
        log.corrected.append(f"publicado {code} v{new_number}: {units} un")


def ensure_yields(session: Session, org_id: UUID, log: ChangeLog) -> None:
    # Mantido só para MANTEIGA-PT (já nasce com yield) e auditoria.
    for code, (units, weight, loss) in YIELDS.items():
        current = _latest_published_fv(session, org_id, code)
        if current is None:
            continue
        if current["yield_units"] == units:
            log.notes.append(f"yield ok {code}={units}")
        else:
            log.notes.append(f"yield pendente {code}: {current['yield_units']}→{units}")


def ensure_product_c(session: Session, world, log: ChangeLog) -> UUID | None:
    """Produto comprado: schema legado sem supply_mode — identificado por código/nome."""
    from app.modules.formula_lab.commands import publish_version

    org_id = world.organization.id
    actor = world.users["demo-formulator"]
    principal = world.principals["demo-formulator"]

    existing = session.execute(
        text("SELECT id FROM technical_product WHERE organization_id=:o AND code='MANTEIGA-PT'"),
        {"o": org_id},
    ).scalar()
    if existing is None:
        pid = seed_uuid("eco", "product", "MANTEIGA-PT")
        session.execute(
            text(
                """
                INSERT INTO technical_product (id, organization_id, code, display_name, description, status)
                VALUES (:id, :org, 'MANTEIGA-PT', 'Manteiga tablete (Demo — comprado)',
                        'Cenário C · produto comprado · sem ordem de produção · valores sintéticos',
                        'active')
                """
            ),
            {"id": pid, "org": org_id},
        )
        log.added.append("produto MANTEIGA-PT (comprado)")
    else:
        pid = existing
        log.skipped.append("produto MANTEIGA-PT já existe")

    fid = session.execute(
        text("SELECT id FROM formulation WHERE organization_id=:o AND code='F-MANTEIGA-PT'"),
        {"o": org_id},
    ).scalar()
    if fid is None:
        fid = seed_uuid("eco", "formulation", "MANTEIGA-PT")
        session.execute(
            text(
                """
                INSERT INTO formulation (id, organization_id, technical_product_id, code, display_name, status)
                VALUES (:id, :org, :tp, 'F-MANTEIGA-PT', 'Manteiga tablete comprada (Demo)', 'active')
                """
            ),
            {"id": fid, "org": org_id, "tp": pid},
        )
        log.added.append("receita F-MANTEIGA-PT (1 embalagem)")

    fvid = session.execute(
        text("SELECT id FROM formulation_version WHERE formulation_id=:f AND version_number=1"),
        {"f": fid},
    ).scalar()
    if fvid is None:
        fvid = seed_uuid("eco", "fv", "MANTEIGA-PT")
        session.execute(
            text(
                """
                INSERT INTO formulation_version
                  (id, organization_id, formulation_id, version_number, status, yield_units,
                   created_by_user_id)
                VALUES (:id, :org, :f, 1, 'draft', 1, :actor)
                """
            ),
            {"id": fvid, "org": org_id, "f": fid, "actor": actor.id},
        )
        manteiga = session.scalar(
            select(Ingredient).where(Ingredient.organization_id == org_id, Ingredient.code == "MANTEIGA")
        )
        iv = session.scalar(
            select(IngredientVersion).where(
                IngredientVersion.ingredient_id == manteiga.id, IngredientVersion.version_number == 1
            )
        )
        session.add(
            FormulationItem(
                organization_id=org_id,
                formulation_version_id=fvid,
                ingredient_version_id=iv.id,
                sequence=1,
                net_quantity=Decimal("500"),
                measurement_unit_id=_unit(session, "g").id,
                correction_factor=Decimal("1"),
                is_flour_basis=False,
                role="ingredient",
                notes="1 embalagem de compra · demonstração",
            )
        )
        session.flush()
        version = session.get(FormulationVersion, fvid)
        helpers.approve_version(session, version, actor, "approved")
        session.flush()
        publish_version(
            session,
            principal,
            fvid,
            expected_version=None,
            idempotency_key=seed_uuid("eco", "pub", "MANTEIGA-PT"),
        )
        log.added.append("versão publicada MANTEIGA-PT yield=1")
    else:
        status = session.execute(
            text("SELECT status FROM formulation_version WHERE id=:id"), {"id": fvid}
        ).scalar()
        if status != "published":
            version = session.get(FormulationVersion, fvid)
            helpers.approve_version(session, version, actor, "approved")
            session.flush()
            publish_version(
                session,
                principal,
                fvid,
                expected_version=None,
                idempotency_key=seed_uuid("eco", "pub", "MANTEIGA-PT"),
            )
            log.corrected.append("MANTEIGA-PT publicado")
        else:
            log.skipped.append("versão MANTEIGA-PT já publicada")
    return fvid



def load_product_ctx(session: Session, org_id: UUID, code: str) -> dict | None:
    row = session.execute(
        text(
            """
            SELECT tp.id AS product_id, fv.id AS version_id, sc.id AS scale_id
            FROM technical_product tp
            JOIN formulation f ON f.technical_product_id = tp.id
            JOIN formulation_version fv ON fv.formulation_id = f.id AND fv.status = 'published'
            LEFT JOIN scale_calculation sc ON sc.formulation_version_id = fv.id
            WHERE tp.organization_id = :org AND tp.code = :code
            ORDER BY fv.version_number DESC
            LIMIT 1
            """
        ),
        {"org": org_id, "code": code},
    ).mappings().first()
    if row is None:
        return None
    version = session.get(FormulationVersion, row["version_id"])
    scale = None if row["scale_id"] is None else session.get(ScaleCalculation, row["scale_id"])
    return {
        "product": SimpleNamespace(id=row["product_id"]),
        "version": version,
        "scale": scale,
    }


def ensure_practiced(session: Session, world, log: ChangeLog) -> None:
    owner = world.principals["demo-owner"]
    specs = (
        ("PAO-FR", (("price-eco-a1", -60, "7.90"), ("price-eco-a2", -30, "8.40"), ("price-eco-a3", 0, "8.90"))),
        ("FOCACCIA", (("price-eco-d1", -45, "18.00"), ("price-eco-d2", -15, "19.50"), ("price-eco-d3", 0, "21.00"))),
        ("BRIOCHE", (("price-eco-brio1", -40, "12.00"), ("price-eco-brio2", -10, "12.80"), ("price-eco-brio3", 0, "13.50"))),
        ("MANTEIGA-PT", (("price-eco-c1", -20, "22.00"), ("price-eco-c2", -7, "23.50"), ("price-eco-c3", 0, "24.90"))),
    )
    for code, points in specs:
        ctx = load_product_ctx(session, world.organization.id, code)
        if ctx is None:
            log.skipped.append(f"preço venda: {code} ausente")
            continue
        for key, days, amount in points:
            body = {
                "technical_product_id": str(ctx["product"].id),
                "channel": "own_counter",
                "amount": amount,
                "currency": "BRL",
                "valid_from": at(ANCHOR, days=days).isoformat(),
                "justification": f"preço demonstração {SCRIPT_TAG} {code}",
            }
            price = create_practiced_price(
                session, owner, body, idempotency_key=seed_uuid("eco", "price", key)
            )
            if price.status == "draft":
                decide_price(
                    session,
                    owner,
                    price.id,
                    {"decision": "publish", "notes": "demonstração", "reinforced_confirmation": True},
                    expected_version=price.row_version,
                    idempotency_key=seed_uuid("eco", "pricepub", key),
                )
                log.added.append(f"preço venda {code} {amount} @ {at(ANCHOR, days=days).date()}")
            else:
                log.skipped.append(f"preço venda {code} {amount} replay")


def ensure_production_variation(session: Session, world, log: ChangeLog) -> None:
    """D: good_units na FOCACCIA completed; A: ordem eco concluída PAO-FR."""
    baker = world.principals["demo-baker"]
    # FOCACCIA completed → good_units 7 (previsto yield 8)
    order_id = session.execute(
        text(
            """
            SELECT po.id FROM production_order po
            JOIN technical_product tp ON tp.id=po.technical_product_id
            WHERE po.organization_id=:org AND tp.code='FOCACCIA' AND po.status='completed'
            ORDER BY po.created_at DESC LIMIT 1
            """
        ),
        {"org": world.organization.id},
    ).scalar()
    if order_id:
        batch = session.scalar(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order_id)
        )
        if batch is not None:
            try:
                before = session.execute(
                    text(
                        """
                        SELECT count(*) FROM production_yield_measurement
                        WHERE idempotency_key = :k
                        """
                    ),
                    {"k": seed_uuid("eco", "yld", "focaccia", "good")},
                ).scalar()
                record_yield(
                    session,
                    baker,
                    batch_id=batch.id,
                    measurement_type=YIELD_GOOD_UNITS,
                    quantity=Decimal("7"),
                    measurement_unit_id=_unit(session, "un").id,
                    idempotency_key=seed_uuid("eco", "yld", "focaccia", "good"),
                    notes="Demonstração D · rendimento vendável 7 un (previsto 8)",
                )
                after = session.execute(
                    text(
                        """
                        SELECT count(*) FROM production_yield_measurement
                        WHERE idempotency_key = :k
                        """
                    ),
                    {"k": seed_uuid("eco", "yld", "focaccia", "good")},
                ).scalar()
                if before == 0 and after == 1:
                    log.added.append("FOCACCIA YIELD_GOOD_UNITS=7")
                else:
                    log.skipped.append("FOCACCIA good_units já registrado")
            except Exception as exc:  # noqa: BLE001
                log.skipped.append(f"FOCACCIA good_units: {exc}")

    # PAO-FR ordem econômica completa
    world.products["PAO-FR"] = load_product_ctx(session, world.organization.id, "PAO-FR")
    if world.products["PAO-FR"] is None or world.products["PAO-FR"]["scale"] is None:
        log.skipped.append("produção PAO-FR: contexto incompleto")
        return
    try:
        with session.begin_nested():
            _advance_production(
                session,
                world,
                "eco-a-paofr",
                "PAO-FR",
                when=ANCHOR,
                shift="morning",
                qty="3300",
                priority=95,
            )
        order = world.orders.get("eco-a-paofr")
        if order is not None:
            batch = session.scalar(
                select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
            )
            if batch is not None:
                record_yield(
                    session,
                    baker,
                    batch_id=batch.id,
                    measurement_type=YIELD_GOOD_UNITS,
                    quantity=Decimal("58"),
                    measurement_unit_id=_unit(session, "un").id,
                    idempotency_key=seed_uuid("eco", "yld", "paofr", "good"),
                    notes="Demonstração A · 58 un boas (previsto 60)",
                )
                log.added.append("ordem eco-a-paofr PAO-FR + GOOD_UNITS=58")
    except Exception as exc:  # noqa: BLE001
        log.skipped.append(f"produção PAO-FR eco: {exc}")


def ensure_calculations(session: Session, world, log: ChangeLog) -> None:
    owner = world.principals["demo-owner"]
    policy = session.scalar(
        select(CostingPolicyVersion)
        .where(
            CostingPolicyVersion.organization_id == world.organization.id,
            CostingPolicyVersion.status == "published",
        )
        .order_by(CostingPolicyVersion.created_at.desc())
    )
    if policy is None:
        raise SystemExit("política publicada ausente")

    def _calc(key: str, body: dict, *key_parts: str) -> None:
        calc = run_calculation(
            session,
            owner,
            body,
            idempotency_key=seed_uuid("eco", "calc", key, *key_parts),
        )
        log.notes.append(
            f"cálculo {key}: id={calc.id} {calc.kind} {calc.completeness} "
            f"total={calc.total_amount} sellable={calc.sellable_unit_amount} qty={calc.sellable_quantity}"
        )

    for code, key in (
        ("PAO-FR", "a-planned"),
        ("PAO-INT", "b-planned"),
        ("FOCACCIA", "d-planned"),
        ("BRIOCHE", "brioche-planned"),
        ("MANTEIGA-PT", "c-planned"),
    ):
        ctx = load_product_ctx(session, world.organization.id, code)
        if ctx is None or ctx["version"] is None:
            log.skipped.append(f"cálculo {code}: sem versão")
            continue
        body = {
            "kind": "planned",
            "policy_version_id": str(policy.id),
            "valuation_at": VALUATION.isoformat(),
            "formulation_version_id": str(ctx["version"].id),
        }
        if ctx["scale"] is not None:
            body["scale_calculation_id"] = str(ctx["scale"].id)
        _calc(key, body, str(ctx["version"].id))

    # Atuais
    for code, key, order_key in (
        ("PAO-FR", "a-actual", "eco-a-paofr"),
        ("FOCACCIA", "d-actual", None),
    ):
        if order_key and world.orders.get(order_key) is not None:
            oid = world.orders[order_key].id
        else:
            oid = session.execute(
                text(
                    """
                    SELECT po.id FROM production_order po
                    JOIN technical_product tp ON tp.id=po.technical_product_id
                    WHERE po.organization_id=:org AND tp.code=:code AND po.status='completed'
                    ORDER BY po.created_at DESC LIMIT 1
                    """
                ),
                {"org": world.organization.id, "code": code},
            ).scalar()
        if oid is None:
            log.skipped.append(f"cálculo atual {code}: sem ordem completed")
            continue
        _calc(
            key,
            {
                "kind": "actual",
                "policy_version_id": str(policy.id),
                "valuation_at": VALUATION.isoformat(),
                "production_order_id": str(oid),
            },
            str(oid),
        )


def write_evidence(before: dict, after: dict, log: ChangeLog, run_label: str) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "script": SCRIPT_TAG,
        "run": run_label,
        "before": before,
        "after": after,
        "log": asdict(log),
        "scenarios": {
            "A": "PAO-FR — custo completo, rendimento, embalagem, previsto+realizado, preços",
            "B": "PAO-INT — incompleto intencional (FAR-INT sem preço)",
            "C": "MANTEIGA-PT — comprado (sem OP)",
            "D": "FOCACCIA — variação good_units 7 vs yield 8 + preços OLEO",
            "E": "futuro — markup produto/família ainda não persistido no contrato",
        },
        "isolation": {
            "panne-demonstracao": "cenário econômico completo",
            "padaria-horizonte-demo": "intencionalmente sem preços/produtos econômicos (só FAR-HZ)",
        },
        "price_basis": "unit_price = preço da embalagem inteira (nunca R$/kg isolado sem package_quantity)",
    }
    (EVIDENCE_DIR / f"run-{run_label}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def run_once(session: Session, run_label: str) -> ChangeLog:
    log = ChangeLog()
    before = photograph(session)
    world = seed_identity(session)
    seed_ingredients(session, world)
    _set_tenant(session, world.organization.id, world.users["demo-owner"].id)

    ensure_prices(session, world.organization.id, log)
    session.flush()
    ensure_product_c(session, world, log)
    session.flush()
    ensure_commercial_versions(session, world, log)
    session.flush()
    ensure_yields(session, world.organization.id, log)
    session.flush()
    ensure_practiced(session, world, log)
    session.flush()
    ensure_production_variation(session, world, log)
    session.flush()
    ensure_calculations(session, world, log)
    session.commit()

    after = photograph(session)
    write_evidence(before, after, log, run_label)
    return log


def main() -> None:
    engine = create_engine(_url(), future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        before0 = photograph(session)
        (EVIDENCE_DIR / "ANTES.json").write_text(
            json.dumps(before0, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )

    print("=== RUN 1 ===")
    with SessionLocal() as session:
        log1 = run_once(session, "1")
        print(f"added={len(log1.added)} corrected={len(log1.corrected)} skipped={len(log1.skipped)}")

    print("=== RUN 2 (idempotência) ===")
    with SessionLocal() as session:
        log2 = run_once(session, "2")
        print(f"added={len(log2.added)} corrected={len(log2.corrected)} skipped={len(log2.skipped)}")

    with SessionLocal() as session:
        after = photograph(session)
        (EVIDENCE_DIR / "DEPOIS.json").write_text(
            json.dumps(after, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )

    # Idempotência: 2ª passagem não deve acrescentar preços/produtos novos relevantes
    new_on_second = [x for x in log2.added if not x.startswith("cálculo")]
    print(f"novos na 2ª passagem (esperado ~0 estruturais): {len(new_on_second)}")
    for line in new_on_second[:20]:
        print("  ", line)
    print("OK", SCRIPT_TAG)


if __name__ == "__main__":
    main()
