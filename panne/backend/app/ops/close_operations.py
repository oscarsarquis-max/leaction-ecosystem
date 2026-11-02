"""Encerra a operação de uma organização por lançamentos, sem apagar nada (CURSOR-032).

    python -m app.ops.close_operations --org <id> --dry-run
    python -m app.ops.close_operations --org <id> --execute --confirm <slug>

Regras:
- O histórico é append-only. Este comando não faz DELETE, não faz SQL de escrita e
  não toca em trigger, RLS ou FK. Tudo é feito pelos comandos do domínio, com o papel
  de runtime (RLS ativo) e o contexto da organização.
- Uma transação só. `--execute` confirma no fim; qualquer erro desfaz tudo.
  `--dry-run` executa os mesmos comandos e desfaz no fim (mostra o efeito real,
  inclusive os erros que o domínio daria).
- Idempotente: cada passo parte do estado atual; na segunda execução não há o que fazer.
- Se um passo não tem comando no domínio, o caso é listado em "sem comando" e pulado.

Passos, nesta ordem:
  1. liberar reservas abertas;
  2. encerrar pedidos de produção (cancela; se já iniciado, encerra como `short_closed`);
     planos são listados (não existe comando de encerrar plano);
  3. cancelar notas fiscais de entrada ainda não confirmadas (as confirmadas ficam);
  4. zerar cada saldo (lote x local) com o ajuste de saída existente;
  5. relatórios e custos não são tocados.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound import commands as fiscal
from app.modules.fiscal_inbound.constants import OPEN_STATUSES as FISCAL_OPEN_STATUSES
from app.modules.fiscal_inbound.models import FiscalInboundDocument
from app.modules.identity_organization.authorization import (
    Association,
    Principal,
    permissions_for_role,
)
from app.modules.identity_organization.models import (
    AppUser,
    Organization,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.modules.identity_organization.tenant_context import apply_tenant_context
from app.modules.inventory_procurement import services as inventory
from app.modules.inventory_procurement.constants import ACTIVE_RESERVATION_STATUSES
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryLocation,
    InventoryLot,
    InventoryReservation,
    ProcurementOrder,
    ProcurementReceipt,
    ProcurementRequisition,
)
from app.modules.production_execution.lifecycle import short_close_order
from app.modules.production_execution.units import canonical_mass_unit
from app.modules.production_planning.commands import cancel_order
from app.modules.production_planning.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_SCHEDULED,
    ORDER_STATUS_SHORT_CLOSED,
    PLAN_STATUS_ARCHIVED,
)
from app.modules.production_planning.models import ProductionOrder, ProductionPlan

REASON = "Encerramento do piloto"
ZERO = Decimal("0")
CANCELLABLE_ORDER_STATUSES = frozenset(
    {ORDER_STATUS_DRAFT, ORDER_STATUS_SCHEDULED, ORDER_STATUS_RELEASED, ORDER_STATUS_ON_HOLD}
)
FINAL_ORDER_STATUSES = frozenset(
    {ORDER_STATUS_COMPLETED, ORDER_STATUS_SHORT_CLOSED, ORDER_STATUS_CANCELLED}
)
PENDING_PROCUREMENT_ORDER_STATUSES = frozenset(
    {"draft", "approved", "issued", "partially_received"}
)
PENDING_REQUISITION_STATUSES = frozenset({"draft", "submitted", "approved"})


class ConfirmationError(Exception):
    """`--confirm` ausente ou diferente do slug da organização."""


class OperatorError(Exception):
    """Não foi possível montar o operador (organização inexistente, sem dono ativo...)."""


@dataclass
class Step:
    key: str
    title: str
    done: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    no_command: list[dict] = field(default_factory=list)
    kept: list[dict] = field(default_factory=list)

    @property
    def affected(self) -> int:
        return len(self.done)

    def as_dict(self) -> dict:
        return {
            "step": self.key,
            "title": self.title,
            "affected": self.affected,
            "errors": len(self.errors),
            "no_command": len(self.no_command),
            "kept": len(self.kept),
            "done": self.done,
            "error_cases": self.errors,
            "no_command_cases": self.no_command,
            "kept_cases": self.kept,
        }


@dataclass
class Report:
    organization_id: UUID
    slug: str
    display_name: str
    mode: str
    steps: list[Step] = field(default_factory=list)
    outside_scope: dict = field(default_factory=dict)
    residual_nonzero_balances: int = 0

    @property
    def errors(self) -> int:
        return sum(len(step.errors) for step in self.steps)

    @property
    def affected(self) -> int:
        return sum(step.affected for step in self.steps)

    @property
    def ok(self) -> bool:
        return self.errors == 0

    def as_dict(self) -> dict:
        return {
            "organization_id": str(self.organization_id),
            "slug": self.slug,
            "display_name": self.display_name,
            "mode": self.mode,
            "ok": self.ok,
            "affected_total": self.affected,
            "errors_total": self.errors,
            "residual_nonzero_balances": self.residual_nonzero_balances,
            "outside_scope": self.outside_scope,
            "steps": [step.as_dict() for step in self.steps],
        }

    def render(self) -> str:
        lines = [
            f"Encerramento da operação: {self.display_name} ({self.slug})"
            f" org={self.organization_id}",
            f"Modo: {self.mode}",
            "",
        ]
        for number, step in enumerate(self.steps, start=1):
            lines.append(
                f"Passo {number} - {step.title}: {step.affected} a afetar/afetado(s), "
                f"{len(step.errors)} erro(s), {len(step.no_command)} sem comando, "
                f"{len(step.kept)} mantido(s)"
            )
            for label, rows in (
                ("  ok", step.done),
                ("  ERRO", step.errors),
                ("  SEM COMANDO", step.no_command),
                ("  mantido", step.kept),
            ):
                for row in rows[:200]:
                    lines.append(f"{label}: {json.dumps(row, ensure_ascii=False, default=str)}")
                if len(rows) > 200:
                    lines.append(f"{label}: ... e mais {len(rows) - 200}")
        lines.append("")
        lines.append(
            f"Saldos diferentes de zero depois dos passos: {self.residual_nonzero_balances}"
        )
        lines.append(
            "Fora dos passos (não alterado, só informado): "
            + json.dumps(self.outside_scope, ensure_ascii=False)
        )
        lines.append(
            f"Total a afetar/afetado: {self.affected}; erros: {self.errors}; "
            f"resultado: {'OK' if self.ok else 'COM ERROS'}"
        )
        return "\n".join(lines)


def _reason_of(exc: Exception) -> str:
    return str(getattr(exc, "reason", None) or exc.__class__.__name__ + ": " + str(exc))[:240]


def _attempt(session: Session, call):
    """Roda um comando de domínio num savepoint. Retorna (resultado, None) ou (None, motivo)."""
    nested = session.begin_nested()
    try:
        result = call()
        session.flush()
        nested.commit()
        return result, None
    except Exception as exc:  # noqa: BLE001 - qualquer recusa do domínio vira caso no relatório
        nested.rollback()
        return None, exc


def build_operator(session: Session, organization_id: UUID) -> tuple[Principal, Organization]:
    """Operador = dono ativo da organização, pelo mesmo caminho de RLS do HTTP."""
    apply_tenant_context(session, organization_id=organization_id, user_id=None)
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise OperatorError("organizacao_inexistente")
    row = session.execute(
        select(OrganizationMembership, OrganizationMembershipRole)
        .join(
            OrganizationMembershipRole,
            OrganizationMembershipRole.membership_id == OrganizationMembership.id,
        )
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == "active",
            OrganizationMembershipRole.role == "owner",
            OrganizationMembershipRole.revoked_at.is_(None),
        )
        .order_by(OrganizationMembershipRole.granted_at, OrganizationMembership.id)
        .limit(1)
    ).first()
    if row is None:
        raise OperatorError("sem_dono_ativo")
    membership = row[0]
    apply_tenant_context(session, organization_id=organization_id, user_id=membership.user_id)
    user = session.get(AppUser, membership.user_id)
    if user is None:
        raise OperatorError("dono_sem_usuario")
    association = Association(
        organization_id=organization_id,
        status=membership.status,
        permissions=permissions_for_role("owner"),
        roles=("owner",),
        organization_display_name=organization.display_name,
        organization_slug=organization.slug,
    )
    apply_tenant_context(
        session,
        organization_id=organization_id,
        user_id=user.id,
        actor_email=user.email,
    )
    principal = Principal(
        user_id=user.id,
        display_name=user.display_name,
        status=user.status,
        issuer="ops:close_operations",
        subject="ops:close_operations",
        associations=(association,),
        selected=association,
    )
    return principal, organization


# ---------------------------------------------------------------- passos


def _step_reservations(session: Session, principal: Principal, org: UUID) -> Step:
    step = Step("reservas", "liberar reservas abertas")
    rows = list(
        session.scalars(
            select(InventoryReservation)
            .where(
                InventoryReservation.organization_id == org,
                InventoryReservation.status.in_(tuple(ACTIVE_RESERVATION_STATUSES)),
            )
            .order_by(InventoryReservation.created_at, InventoryReservation.id)
        )
    )
    for row in rows:
        ref = {
            "reserva": str(row.id),
            "pedido": str(row.production_order_id),
            "status": row.status,
            "quantidade": format(Decimal(row.reserved_quantity), "f"),
        }
        _, exc = _attempt(
            session,
            lambda row=row: inventory.release_reservation(
                session,
                principal,
                row.id,
                expected_version=row.row_version,
                idempotency_key=uuid4(),
            ),
        )
        if exc is None:
            step.done.append({**ref, "acao": "liberada"})
        else:
            step.errors.append({**ref, "erro": _reason_of(exc)})
    return step


def _step_production(session: Session, principal: Principal, org: UUID) -> Step:
    step = Step("producao", "encerrar pedidos de produção (planos só listados)")
    orders = list(
        session.scalars(
            select(ProductionOrder)
            .where(
                ProductionOrder.organization_id == org,
                ProductionOrder.status.notin_(tuple(FINAL_ORDER_STATUSES)),
            )
            .order_by(ProductionOrder.created_at, ProductionOrder.id)
        )
    )
    for order in orders:
        ref = {"pedido": order.public_code, "id": str(order.id), "status": order.status}
        started = order.status not in CANCELLABLE_ORDER_STATUSES
        if not started:
            _, exc = _attempt(
                session,
                lambda order=order: cancel_order(
                    session,
                    principal,
                    order_id=order.id,
                    reason=REASON,
                    idempotency_key=uuid4(),
                ),
            )
            if exc is None:
                step.done.append({**ref, "acao": "cancelado"})
                continue
            if _reason_of(exc) != "cancelamento_incompativel":
                step.errors.append({**ref, "acao": "cancelar", "erro": _reason_of(exc)})
                continue
            # já tem fato de execução: o domínio só aceita encerrar antes do fim.
        _, exc = _attempt(
            session,
            lambda order=order: short_close_order(
                session,
                principal,
                order_id=order.id,
                reason=REASON,
                idempotency_key=uuid4(),
            ),
        )
        if exc is None:
            step.done.append({**ref, "acao": "encerrado antes do fim (short_closed)"})
        else:
            step.errors.append({**ref, "acao": "short_closed", "erro": _reason_of(exc)})
    plans = list(
        session.scalars(
            select(ProductionPlan)
            .where(
                ProductionPlan.organization_id == org,
                ProductionPlan.status != PLAN_STATUS_ARCHIVED,
            )
            .order_by(ProductionPlan.created_at, ProductionPlan.id)
        )
    )
    for plan in plans:
        step.no_command.append(
            {
                "plano": plan.public_code,
                "id": str(plan.id),
                "status": plan.status,
                "motivo": "não existe comando de encerrar/arquivar plano no domínio",
            }
        )
    return step


def _step_fiscal(session: Session, principal: Principal, org: UUID) -> Step:
    step = Step("notas", "cancelar notas de entrada não confirmadas")
    docs = list(
        session.scalars(
            select(FiscalInboundDocument)
            .where(
                FiscalInboundDocument.organization_id == org,
                FiscalInboundDocument.status.in_(tuple(FISCAL_OPEN_STATUSES)),
            )
            .order_by(FiscalInboundDocument.created_at, FiscalInboundDocument.id)
        )
    )
    for doc in docs:
        ref = {
            "nota": str(doc.number or doc.id),
            "id": str(doc.id),
            "status": doc.status,
        }
        if fiscal._has_receipt(session, org, doc.id):  # recebimento já lançado = histórico
            step.kept.append(
                {**ref, "motivo": "recebimento já lançado; cancelar a nota não desfaz o estoque"}
            )
            continue
        _, exc = _attempt(
            session,
            lambda doc=doc: fiscal.cancel_document(
                session,
                principal,
                doc.id,
                {"reason": REASON},
                idempotency_key=uuid4(),
            ),
        )
        if exc is None:
            step.done.append({**ref, "acao": "cancelada"})
        else:
            step.errors.append({**ref, "erro": _reason_of(exc)})
    drafts = list(
        session.scalars(
            select(ProcurementReceipt).where(
                ProcurementReceipt.organization_id == org,
                ProcurementReceipt.status == "draft",
            )
        )
    )
    for receipt in drafts:
        step.no_command.append(
            {
                "recebimento": receipt.public_code,
                "id": str(receipt.id),
                "status": receipt.status,
                "motivo": "não existe comando de cancelar recebimento de compra no domínio",
            }
        )
    return step


def _adjust_unit(session: Session, balance: InventoryBalance) -> str:
    unit = inventory.resolve_measurement_unit(session, balance.unit_code)
    if unit.dimension == "mass":
        # o saldo físico é guardado na unidade canônica de massa
        return canonical_mass_unit(session).code
    return unit.code


def _step_balances(session: Session, principal: Principal, org: UUID) -> Step:
    step = Step("saldos", "zerar saldos (ajuste de saída por lote e local)")
    balances = list(
        session.scalars(
            select(InventoryBalance)
            .where(InventoryBalance.organization_id == org, InventoryBalance.physical_quantity != 0)
            .order_by(
                InventoryBalance.inventory_location_id,
                InventoryBalance.inventory_item_id,
                InventoryBalance.inventory_lot_id,
            )
        )
    )
    for balance in balances:
        lot = session.get(InventoryLot, balance.inventory_lot_id)
        location = session.get(InventoryLocation, balance.inventory_location_id)
        physical = Decimal(balance.physical_quantity)
        ref = {
            "lote": getattr(lot, "internal_lot_code", str(balance.inventory_lot_id)),
            "local": getattr(location, "code", str(balance.inventory_location_id)),
            "saldo": format(physical, "f"),
            "unidade": balance.unit_code,
        }
        if physical < ZERO:
            step.no_command.append(
                {**ref, "motivo": "saldo negativo; o encerramento só tem ajuste de saída"}
            )
            continue
        unit_code = _adjust_unit(session, balance)

        def post(override: bool, balance=balance, physical=physical, unit_code=unit_code):
            body = {
                "movement_type": "adjust_minus",
                "inventory_item_id": str(balance.inventory_item_id),
                "inventory_lot_id": str(balance.inventory_lot_id),
                "from_location_id": str(balance.inventory_location_id),
                "quantity": format(physical, "f"),
                "unit_code": unit_code,
                "origin_type": "manual",
                "reason": REASON,
                "approved": True,
            }
            if override:
                body["expired_override"] = True
            return inventory.post_movement(session, principal, body, idempotency_key=uuid4())

        _, exc = _attempt(session, lambda: post(False))
        override_used = False
        if exc is not None and _reason_of(exc) == "lote_indisponivel":
            override_used = True
            _, exc = _attempt(session, lambda: post(True))
        if exc is None:
            step.done.append(
                {
                    **ref,
                    "acao": "ajuste de saída até zero",
                    **(
                        {"observacao": "lote vencido/bloqueado: usado o override do domínio"}
                        if override_used
                        else {}
                    ),
                }
            )
        else:
            step.errors.append({**ref, "erro": _reason_of(exc)})
    return step


def _outside_scope(session: Session, org: UUID) -> dict:
    orders = session.scalars(
        select(ProcurementOrder.status).where(ProcurementOrder.organization_id == org)
    ).all()
    requisitions = session.scalars(
        select(ProcurementRequisition.status).where(ProcurementRequisition.organization_id == org)
    ).all()
    return {
        "pedidos_de_compra_pendentes": sum(
            1 for s in orders if s in PENDING_PROCUREMENT_ORDER_STATUSES
        ),
        "requisicoes_de_compra_pendentes": sum(
            1 for s in requisitions if s in PENDING_REQUISITION_STATUSES
        ),
    }


def _residual(session: Session, org: UUID) -> int:
    rows = session.scalars(
        select(InventoryBalance.id).where(
            InventoryBalance.organization_id == org, InventoryBalance.physical_quantity != 0
        )
    ).all()
    return len(rows)


def close_operations(
    session: Session,
    *,
    organization_id: UUID,
    execute: bool,
    confirm: str | None = None,
) -> Report:
    """Faz os passos na transação da `session`. Quem chama decide commit ou rollback."""
    principal, organization = build_operator(session, organization_id)
    if execute and confirm != organization.slug:
        raise ConfirmationError("confirmacao_invalida")
    report = Report(
        organization_id=organization_id,
        slug=organization.slug,
        display_name=organization.display_name,
        mode="execute" if execute else "dry-run",
    )
    report.steps.append(_step_reservations(session, principal, organization_id))
    report.steps.append(_step_production(session, principal, organization_id))
    report.steps.append(_step_fiscal(session, principal, organization_id))
    report.steps.append(_step_balances(session, principal, organization_id))
    report.residual_nonzero_balances = _residual(session, organization_id)
    report.outside_scope = _outside_scope(session, organization_id)
    return report


# ---------------------------------------------------------------- CLI


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.close_operations",
        description="Encerra a operação de uma organização por lançamentos (sem apagar).",
    )
    parser.add_argument("--org", required=True, help="id (UUID) da organização")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="simula e desfaz")
    mode.add_argument("--execute", action="store_true", help="aplica (exige --confirm <slug>)")
    parser.add_argument("--confirm", default=None, help="slug da organização")
    return parser


def main(argv: list[str] | None = None, *, session_factory=None) -> int:
    args = _parser().parse_args(argv)
    try:
        organization_id = UUID(args.org)
    except ValueError:
        print("ERRO: --org precisa ser um UUID", file=sys.stderr)
        return 2
    if session_factory is None:
        from app.db import RuntimeSessionLocal

        session_factory = RuntimeSessionLocal
    if session_factory is None:
        print("ERRO: papel de runtime indisponível (PANNE_RUNTIME_DATABASE_URL)", file=sys.stderr)
        return 2
    session = session_factory()
    try:
        try:
            report = close_operations(
                session,
                organization_id=organization_id,
                execute=bool(args.execute),
                confirm=args.confirm,
            )
        except ConfirmationError:
            session.rollback()
            print(
                "RECUSADO: --confirm precisa ser exatamente o slug da organização.", file=sys.stderr
            )
            return 3
        except OperatorError as exc:
            session.rollback()
            print(f"ERRO: {exc}", file=sys.stderr)
            return 2
        print(report.render())
        print("RESULT_JSON " + json.dumps(report.as_dict(), ensure_ascii=False, default=str))
        if args.execute and report.ok:
            session.commit()
            print("COMMIT: encerramento aplicado.")
            return 0
        session.rollback()
        if args.execute:
            print("ROLLBACK: houve erros; nada foi aplicado.", file=sys.stderr)
            return 1
        print("ROLLBACK: dry-run não altera nada.")
        return 0 if report.ok else 1
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
