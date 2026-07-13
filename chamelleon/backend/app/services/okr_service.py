"""Serviço de Planejamento Estratégico (OKR)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from flask import g

from app.database.models import db
from app.models.okr_models import OkrDriver, OkrKeyResult, OkrKpi, OkrObjective
from app.services.okr_canonical import CANONICAL_OKR_MATRIX


def ensure_canonical_okrs_for_tenant(
    tenant_id: uuid.UUID | str,
    *,
    commit: bool = True,
) -> bool:
    """Injeta a matriz PanelDX no tenant se ainda não houver direcionadores."""
    return OkrService().ensure_canonical_seed(tenant_id=tenant_id, commit=commit)


def ensure_canonical_okrs_for_all_tenants() -> int:
    """Backfill: aplica matriz canônica em todos os tenants sem OKRs.

    Returns:
        Quantidade de tenants que receberam o seed nesta execução.
    """
    from app.database.models import Tenant

    seeded_count = 0
    for tenant in Tenant.query.order_by(Tenant.created_at.asc()).all():
        if OkrService().ensure_canonical_seed(tenant_id=tenant.id, commit=False):
            seeded_count += 1
    if seeded_count:
        db.session.commit()
    return seeded_count


class OkrService:
    def _tenant_id(self) -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))

    def _resolve_tenant_id(self, tenant_id: uuid.UUID | str | None = None) -> uuid.UUID:
        if tenant_id is None:
            return self._tenant_id()
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))

    def ensure_canonical_seed(
        self,
        tenant_id: uuid.UUID | str | None = None,
        *,
        commit: bool = True,
    ) -> bool:
        """Injeta a matriz PanelDX se o tenant ainda não possui direcionadores.

        Padrão de onboarding: todo cliente/indústria novo nasce com os 5
        direcionadores canônicos (objetivos, KRs e KPIs sugeridos). O gestor
        pode alterar/criar itens depois; este seed só corre quando o tenant
        ainda não tem nenhum direcionador.

        Returns:
            True se o seed foi aplicado nesta chamada.
        """
        resolved_tenant_id = self._resolve_tenant_id(tenant_id)
        existing = (
            db.session.query(OkrDriver.id)
            .filter(OkrDriver.tenant_id == resolved_tenant_id)
            .limit(1)
            .first()
        )
        if existing:
            return False

        for item in CANONICAL_OKR_MATRIX:
            driver = OkrDriver(
                tenant_id=resolved_tenant_id,
                name=item["name"],
                sort_order=int(item["sort_order"]),
            )
            db.session.add(driver)
            db.session.flush()

            objective = OkrObjective(
                tenant_id=resolved_tenant_id,
                driver_id=driver.id,
                description=item["objective"],
            )
            db.session.add(objective)
            db.session.flush()

            for kr in item["key_results"]:
                db.session.add(
                    OkrKeyResult(
                        tenant_id=resolved_tenant_id,
                        objective_id=objective.id,
                        description=kr["description"],
                        target_value=float(kr["target_value"]),
                        current_value=0.0,
                        metric_unit=kr.get("metric_unit") or "%",
                    )
                )

            for kpi in item["kpis"]:
                db.session.add(
                    OkrKpi(
                        tenant_id=resolved_tenant_id,
                        driver_id=driver.id,
                        name=kpi["name"],
                        target_value=0.0,
                        current_value=0.0,
                        is_financial=bool(kpi.get("is_financial")),
                        metric_unit=kpi.get("metric_unit"),
                    )
                )

        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return True

    def list_dashboard(self) -> dict[str, Any]:
        """Garante seed e devolve árvore completa ordenada por direcionador."""
        seeded = self.ensure_canonical_seed()
        tenant_id = self._tenant_id()
        drivers = (
            db.session.query(OkrDriver)
            .filter(OkrDriver.tenant_id == tenant_id)
            .order_by(OkrDriver.sort_order.asc(), OkrDriver.name.asc())
            .all()
        )
        return {
            "seeded": seeded,
            "drivers": [d.to_dict(include_tree=True) for d in drivers],
        }

    def update_key_result(self, kr_id: str, payload: dict[str, Any]) -> OkrKeyResult:
        tenant_id = self._tenant_id()
        kr = (
            db.session.query(OkrKeyResult)
            .filter(
                OkrKeyResult.id == uuid.UUID(str(kr_id)),
                OkrKeyResult.tenant_id == tenant_id,
            )
            .first()
        )
        if not kr:
            raise ValueError("Key Result não encontrado.")

        if "current_value" in payload and payload["current_value"] is not None:
            kr.current_value = float(payload["current_value"])
        if "target_value" in payload and payload["target_value"] is not None:
            kr.target_value = float(payload["target_value"])
        if payload.get("description"):
            kr.description = str(payload["description"]).strip()
        if payload.get("metric_unit"):
            kr.metric_unit = str(payload["metric_unit"]).strip()[:64]

        db.session.commit()
        db.session.refresh(kr)
        return kr

    def update_kpi(self, kpi_id: str, payload: dict[str, Any]) -> OkrKpi:
        tenant_id = self._tenant_id()
        kpi = (
            db.session.query(OkrKpi)
            .filter(
                OkrKpi.id == uuid.UUID(str(kpi_id)),
                OkrKpi.tenant_id == tenant_id,
            )
            .first()
        )
        if not kpi:
            raise ValueError("KPI não encontrado.")

        if "current_value" in payload and payload["current_value"] is not None:
            kpi.current_value = float(payload["current_value"])
        if "target_value" in payload and payload["target_value"] is not None:
            kpi.target_value = float(payload["target_value"])
        if payload.get("name"):
            kpi.name = str(payload["name"]).strip()[:255]
        if "is_financial" in payload and payload["is_financial"] is not None:
            kpi.is_financial = bool(payload["is_financial"])
        if "metric_unit" in payload:
            unit = payload["metric_unit"]
            kpi.metric_unit = str(unit).strip()[:64] if unit else None

        db.session.commit()
        db.session.refresh(kpi)
        return kpi

    def _next_sort_order(self, tenant_id: uuid.UUID) -> int:
        current = (
            db.session.query(func.max(OkrDriver.sort_order))
            .filter(OkrDriver.tenant_id == tenant_id)
            .scalar()
        )
        return int(current or 0) + 1

    def _driver_tree(self, driver_id: uuid.UUID) -> OkrDriver:
        driver = (
            db.session.query(OkrDriver)
            .filter(
                OkrDriver.id == driver_id,
                OkrDriver.tenant_id == self._tenant_id(),
            )
            .first()
        )
        if not driver:
            raise ValueError("Direcionador não encontrado.")
        return driver

    def _get_driver(self, driver_id: str) -> OkrDriver:
        tenant_id = self._tenant_id()
        driver = (
            db.session.query(OkrDriver)
            .filter(
                OkrDriver.id == uuid.UUID(str(driver_id)),
                OkrDriver.tenant_id == tenant_id,
            )
            .first()
        )
        if not driver:
            raise ValueError("Direcionador não encontrado.")
        return driver

    def _get_objective(self, objective_id: str) -> OkrObjective:
        tenant_id = self._tenant_id()
        objective = (
            db.session.query(OkrObjective)
            .filter(
                OkrObjective.id == uuid.UUID(str(objective_id)),
                OkrObjective.tenant_id == tenant_id,
            )
            .first()
        )
        if not objective:
            raise ValueError("Objetivo não encontrado.")
        return objective

    def create_driver(self, payload: dict[str, Any]) -> OkrDriver:
        tenant_id = self._tenant_id()
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Informe o nome do direcionador.")

        sort_order = payload.get("sort_order")
        if sort_order is None:
            sort_order = self._next_sort_order(tenant_id)
        else:
            sort_order = int(sort_order)

        driver = OkrDriver(
            tenant_id=tenant_id,
            name=name[:255],
            sort_order=sort_order,
        )
        db.session.add(driver)
        db.session.flush()

        objective_desc = str(payload.get("objective") or payload.get("objective_description") or "").strip()
        if objective_desc:
            db.session.add(
                OkrObjective(
                    tenant_id=tenant_id,
                    driver_id=driver.id,
                    description=objective_desc,
                )
            )

        db.session.commit()
        return self._driver_tree(driver.id)

    def create_objective(self, payload: dict[str, Any]) -> OkrObjective:
        tenant_id = self._tenant_id()
        driver_id = payload.get("driver_id")
        if not driver_id:
            raise ValueError("Informe o direcionador (driver_id).")
        driver = self._get_driver(str(driver_id))

        description = str(payload.get("description") or "").strip()
        if not description:
            raise ValueError("Informe a descrição do objetivo.")

        objective = OkrObjective(
            tenant_id=tenant_id,
            driver_id=driver.id,
            description=description,
        )
        db.session.add(objective)
        db.session.commit()
        db.session.refresh(objective)
        return objective

    def create_key_result(self, payload: dict[str, Any]) -> OkrKeyResult:
        tenant_id = self._tenant_id()
        objective_id = payload.get("objective_id")
        driver_id = payload.get("driver_id")

        if objective_id:
            objective = self._get_objective(str(objective_id))
        elif driver_id:
            driver = self._get_driver(str(driver_id))
            if not driver.objectives:
                raise ValueError(
                    "Este direcionador ainda não tem objetivo. Crie um objetivo antes do KR."
                )
            objective = driver.objectives[0]
        else:
            raise ValueError("Informe objective_id ou driver_id.")

        description = str(payload.get("description") or "").strip()
        if not description:
            raise ValueError("Informe a descrição do Key Result.")

        target_value = float(payload.get("target_value") if payload.get("target_value") is not None else 0)
        current_value = float(payload.get("current_value") if payload.get("current_value") is not None else 0)
        metric_unit = str(payload.get("metric_unit") or "%").strip()[:64] or "%"

        kr = OkrKeyResult(
            tenant_id=tenant_id,
            objective_id=objective.id,
            description=description,
            target_value=target_value,
            current_value=current_value,
            metric_unit=metric_unit,
        )
        db.session.add(kr)
        db.session.commit()
        db.session.refresh(kr)
        return kr

    def create_kpi(self, payload: dict[str, Any]) -> OkrKpi:
        tenant_id = self._tenant_id()
        driver_id = payload.get("driver_id")
        if not driver_id:
            raise ValueError("Informe o direcionador (driver_id).")
        driver = self._get_driver(str(driver_id))

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Informe o nome do KPI.")

        target_value = float(payload.get("target_value") if payload.get("target_value") is not None else 0)
        current_value = float(payload.get("current_value") if payload.get("current_value") is not None else 0)
        is_financial = bool(payload.get("is_financial"))
        unit = payload.get("metric_unit")
        metric_unit = str(unit).strip()[:64] if unit else ("R$" if is_financial else None)

        kpi = OkrKpi(
            tenant_id=tenant_id,
            driver_id=driver.id,
            name=name[:255],
            target_value=target_value,
            current_value=current_value,
            is_financial=is_financial,
            metric_unit=metric_unit,
        )
        db.session.add(kpi)
        db.session.commit()
        db.session.refresh(kpi)
        return kpi
