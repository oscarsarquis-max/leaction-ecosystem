"""Seis jornadas smoke. Resultado, duração, entidades e motivo de falha."""

from __future__ import annotations

import time
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.models import AiProposal
from app.modules.costing_pricing.models import CostingCalculation, PricingSimulation
from app.modules.formula_lab.models import FormulationVersion, ScaleCalculation, TechnicalProduct
from app.modules.identity_organization.models import AuthIdentity, Organization, OrganizationMembership
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion, MeasurementUnit, SupplierItem
from app.modules.inventory_procurement.models import (
    InventoryConsumptionPosting,
    InventoryLot,
    InventoryPick,
    InventoryReservation,
    ProcurementOrder,
    ProcurementQuotation,
    ProcurementReceipt,
    ProcurementRequisition,
    ProcurementReturn,
)
from app.modules.labeling_compliance.models import LabelingDossier
from app.modules.production_planning.models import ProductionOrder, ProductionPlan
from app.modules.reporting_analytics.models import ReportingSavedView, ReportingSnapshot
from app.seed.demo import ORG_A, ORG_B, seed_demo
from app.seed.reference import seed_reference

SCENARIOS = ("application", "recipe", "production", "compliance", "inventory", "reports")


def _timed(name: str, fn) -> dict:
    started = time.perf_counter()
    try:
        payload = fn()
        ok = bool(payload.get("ok"))
        error = None if ok else payload.get("error") or "critério não atendido"
    except Exception as exc:
        payload = {}
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "name": name,
        "ok": ok,
        "duration_ms": elapsed_ms,
        "entities": payload.get("entities") or {},
        "error": error,
    }


def seed_smoke(session: Session, *, scenario: str, anchor: date) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"cenário desconhecido: {scenario}")
    seed_reference(session)
    world = seed_demo(session, anchor=anchor)
    journey = JOURNEYS[scenario](session)
    return {
        "scenario": scenario,
        "organization": world.organization.slug,
        "gaps": world.gaps,
        "journey": journey,
    }


def journey_application(session: Session) -> dict:
    orgs = list(session.scalars(select(Organization)))
    slugs = {row.slug for row in orgs}
    units = int(session.scalar(select(func.count()).select_from(MeasurementUnit)) or 0)
    identities = int(session.scalar(select(func.count()).select_from(AuthIdentity)) or 0)
    owner = session.scalar(select(AuthIdentity).where(AuthIdentity.subject == "demo-owner"))
    memberships = 0
    if owner is not None:
        memberships = int(
            session.scalar(
                select(func.count())
                .select_from(OrganizationMembership)
                .where(OrganizationMembership.user_id == owner.user_id)
            )
            or 0
        )
    other_hidden = 0
    org_a = next((row for row in orgs if row.slug == ORG_A), None)
    org_b = next((row for row in orgs if row.slug == ORG_B), None)
    if org_a is not None and org_b is not None:
        other_hidden = int(
            session.scalar(
                select(func.count())
                .select_from(Ingredient)
                .where(Ingredient.organization_id == org_b.id, Ingredient.code == "FAR-TRIGO")
            )
            or 0
        )
    ok = (
        ORG_A in slugs
        and ORG_B in slugs
        and units >= 3
        and identities >= 7
        and memberships >= 2
        and other_hidden == 0
        and owner is not None
    )
    return {
        "ok": ok,
        "entities": {
            "organizations": sorted(slugs),
            "units": units,
            "identities": identities,
            "owner_memberships": memberships,
            "rls_farinha_org_b": other_hidden,
        },
        "error": None if ok else "organizações, /me (identidade), troca de org ou RLS A/B incompletos",
    }


def journey_recipe(session: Session) -> dict:
    ingredients = int(session.scalar(select(func.count()).select_from(Ingredient)) or 0)
    published = int(
        session.scalar(select(func.count()).select_from(IngredientVersion).where(IngredientVersion.status == "published"))
        or 0
    )
    products = int(session.scalar(select(func.count()).select_from(TechnicalProduct)) or 0)
    versions = int(session.scalar(select(func.count()).select_from(FormulationVersion)) or 0)
    scales = int(session.scalar(select(func.count()).select_from(ScaleCalculation)) or 0)
    proposals = int(session.scalar(select(func.count()).select_from(AiProposal)) or 0)
    ok = ingredients >= 10 and published >= 8 and products >= 3 and versions >= 3 and scales >= 1 and proposals >= 1
    return {
        "ok": ok,
        "entities": {
            "ingredients": ingredients,
            "published_versions": published,
            "products": products,
            "formulation_versions": versions,
            "scale_calculations": scales,
            "ai_proposals": proposals,
        },
        "error": None if ok else "catálogo, publicação, escala ou proposta falsa incompletos",
    }


def journey_production(session: Session) -> dict:
    plans = int(session.scalar(select(func.count()).select_from(ProductionPlan)) or 0)
    statuses = list(session.scalars(select(ProductionOrder.status)))
    expected = {
        "draft",
        "scheduled",
        "released",
        "in_weighing",
        "ready",
        "in_progress",
        "on_hold",
        "completed",
        "short_closed",
        "cancelled",
    }
    ok = plans >= 1 and len(statuses) >= 8 and expected.issubset(set(statuses))
    return {
        "ok": ok,
        "entities": {"plans": plans, "orders": len(statuses), "statuses": sorted(set(statuses))},
        "error": None if ok else f"faltam estados de produção: {sorted(expected - set(statuses))}",
    }


def journey_compliance(session: Session) -> dict:
    dossiers = list(session.scalars(select(LabelingDossier)))
    calcs = list(session.scalars(select(CostingCalculation)))
    sims = int(session.scalar(select(func.count()).select_from(PricingSimulation)) or 0)
    kinds = {row.kind for row in calcs}
    ok = len(dossiers) >= 2 and {"planned", "actual"} <= kinds and sims >= 1
    return {
        "ok": ok,
        "entities": {
            "dossiers": len(dossiers),
            "dossier_statuses": sorted({row.status for row in dossiers}),
            "cost_calculations": len(calcs),
            "calculation_kinds": sorted(str(item) for item in kinds if item),
            "simulations": sims,
        },
        "error": None if ok else "dossiê, custo previsto/realizado ou simulação ausentes",
    }


def journey_inventory(session: Session) -> dict:
    lots = int(session.scalar(select(func.count()).select_from(InventoryLot)) or 0)
    reservations = int(session.scalar(select(func.count()).select_from(InventoryReservation)) or 0)
    picks = int(session.scalar(select(func.count()).select_from(InventoryPick)) or 0)
    postings = int(session.scalar(select(func.count()).select_from(InventoryConsumptionPosting)) or 0)
    requisitions = list(session.scalars(select(ProcurementRequisition.status)))
    quotes = int(session.scalar(select(func.count()).select_from(ProcurementQuotation)) or 0)
    orders = list(session.scalars(select(ProcurementOrder.status)))
    receipts = int(session.scalar(select(func.count()).select_from(ProcurementReceipt)) or 0)
    returns = int(session.scalar(select(func.count()).select_from(ProcurementReturn)) or 0)
    priced = int(session.scalar(select(func.count()).select_from(SupplierItem)) or 0)
    req_set = set(requisitions)
    order_set = set(orders)
    ok = (
        lots >= 4
        and reservations >= 1
        and quotes >= 2
        and receipts >= 2
        and returns >= 1
        and priced >= 1
        and {"draft", "submitted", "approved", "converted"} <= req_set
        and {"partially_received", "received"} <= order_set
    )
    return {
        "ok": ok,
        "entities": {
            "lots": lots,
            "reservations": reservations,
            "picks": picks,
            "consumption_postings": postings,
            "requisition_statuses": sorted(req_set),
            "quotations": quotes,
            "order_statuses": sorted(order_set),
            "receipts": receipts,
            "returns": returns,
        },
        "error": None
        if ok
        else "estoque ou compras incompletos (lote, reserva, requisição, cotação, pedido, recebimento ou devolução)",
    }


def journey_reports(session: Session) -> dict:
    views = int(session.scalar(select(func.count()).select_from(ReportingSavedView)) or 0)
    snapshots = int(session.scalar(select(func.count()).select_from(ReportingSnapshot)) or 0)
    board = int(session.scalar(select(func.count()).select_from(ProductionOrder)) or 0)
    ok = views >= 1 and snapshots >= 1 and board >= 5
    return {
        "ok": ok,
        "entities": {"saved_views": views, "snapshots": snapshots, "board_orders": board},
        "error": None if ok else "visão salva, snapshot ou quadro ausentes",
    }


JOURNEYS = {
    "application": journey_application,
    "recipe": journey_recipe,
    "production": journey_production,
    "compliance": journey_compliance,
    "inventory": journey_inventory,
    "reports": journey_reports,
}


def run_journeys(session: Session) -> dict[str, dict]:
    return {name: _timed(name, lambda fn=fn: fn(session)) for name, fn in JOURNEYS.items()}
