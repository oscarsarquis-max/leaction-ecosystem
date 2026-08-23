"""Casos de uso HTTP do assistente. Reusa gateway, grounding e revisão."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.fake_gateway import FakeModelGateway
from app.modules.ai_orchestration.gateway import GatewayError, ModelGateway
from app.modules.ai_orchestration.guided import sanitize_guided_input
from app.modules.ai_orchestration.guardrails import GuardrailError, map_gateway_failure
from app.modules.ai_orchestration.limits import runtime_limits
from app.modules.ai_orchestration.models import AiProposal
from app.modules.ai_orchestration.orchestrate import (
    OrchestrationError,
    ProposalCommand,
    run_proposal,
)
from app.modules.ai_orchestration.review import (
    decide_changes,
    materialize_proposal,
    review_proposal,
)
from app.modules.formula_lab.commands import _replay, _remember
from app.modules.formula_lab.models import FormulationVersion
from app.modules.identity_organization.authorization import (
    PERMISSION_RECIPE_AI_MATERIALIZE,
    PERMISSION_RECIPE_AI_PROPOSE,
    PERMISSION_RECIPE_AI_REVIEW,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.production_planning.errors import (
    ConcurrencyError,
    InvalidStateError,
    ValidationError,
)


class RecipeAiError(ValidationError):
    pass


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _proposal(session: Session, organization_id: UUID, proposal_id: UUID) -> AiProposal:
    row = session.get(AiProposal, proposal_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _match(proposal: AiProposal, expected: int | None) -> None:
    if expected is not None and int(proposal.row_version or 1) != expected:
        raise ConcurrencyError("versao_conflito")


def _public_error(exc: Exception) -> RecipeAiError:
    if isinstance(exc, GuardrailError):
        return RecipeAiError(exc.code)
    if isinstance(exc, OrchestrationError):
        text = str(exc)
        mapping = {
            "grounding_insufficient": "grounding_insuficiente",
            "citação inventada": "citacao_invalida",
            "citação inválida": "citacao_invalida",
            "ID inventado": "id_inventado",
            "aceitação recusa itens pendentes": "item_nao_resolvido",
            "proposta já materializada": "proposta_ja_materializada",
            "proposta não materializável": "proposta_invalida",
            "proposta não revisável": "proposta_invalida",
        }
        return RecipeAiError(mapping.get(text, "proposta_invalida"))
    if isinstance(exc, GatewayError):
        code, _ = map_gateway_failure(exc)
        return RecipeAiError(code)
    return RecipeAiError("contrato_invalido")


def propose_recipe(
    session: Session,
    principal: Principal,
    payload: dict,
    *,
    idempotency_key: UUID,
    gateway: ModelGateway | None = None,
) -> AiProposal | None:
    require_permission(principal, PERMISSION_RECIPE_AI_PROPOSE)
    organization_id = _org(principal)
    try:
        guided = sanitize_guided_input(payload)
    except GuardrailError as exc:
        raise _public_error(exc) from exc
    digest_payload = guided.as_canonical()
    replay = _replay(session, organization_id, idempotency_key, "recipe.ai.propose", digest_payload)
    if replay is not None:
        return session.get(AiProposal, replay.resource_id)
    active = session.scalar(
        select(func.count())
        .select_from(AiProposal)
        .where(
            AiProposal.organization_id == organization_id,
            AiProposal.status.in_(
                ("requested", "retrieving_evidence", "generating", "awaiting_review", "draft")
            ),
        )
    )
    limits = runtime_limits()
    if int(active or 0) >= int(limits["max_concurrent"]):
        raise RecipeAiError("concorrencia_excedida")
    if guided.intent == "adapt_recipe" and guided.base_formulation_version_id:
        base = session.get(FormulationVersion, guided.base_formulation_version_id)
        if base is None or base.organization_id != organization_id:
            raise ValidationError("recurso_nao_encontrado")
    chosen = gateway or FakeModelGateway()
    command = ProposalCommand(
        organization_id=organization_id,
        objective=guided.objective,
        interaction_type=(
            "adapt_formulation_proposal"
            if guided.intent == "adapt_recipe"
            else "create_formulation_proposal"
        ),
        allowed_ingredient_version_ids=guided.allowed_ingredient_version_ids,
        base_formulation_version_id=guided.base_formulation_version_id,
        created_by_user_id=principal.user_id,
        intent=guided.intent,
        constraints=guided.process_limits + guided.technical_traits,
        retrieval_profile={
            "jurisdiction": guided.jurisdiction,
            "selected_references": [str(item) for item in guided.selected_reference_ids],
        },
        guided_input=guided.as_canonical(),
        jurisdiction=guided.jurisdiction,
        regulatory_purpose=guided.regulatory_purpose,
        selected_knowledge_source_ids=guided.selected_knowledge_source_ids,
    )
    try:
        result = run_proposal(session, command, chosen)
    except (OrchestrationError, GuardrailError, GatewayError) as exc:
        raise _public_error(exc) from exc
    if result.error_code == "grounding_insufficient":
        stub = AiProposal(
            organization_id=organization_id,
            ai_interaction_id=result.interaction.id,
            proposal_type="adapt" if guided.intent == "adapt_recipe" else "create",
            base_formulation_version_id=guided.base_formulation_version_id,
            title="Proposta sem evidência suficiente",
            objective_summary=guided.objective,
            status="grounding_insufficient",
            assumptions=[],
            unresolved_questions=["Evidência insuficiente para gerar a proposta."],
            warnings=["As fontes recuperadas não sustentam a geração."],
            intent=guided.intent,
            guided_input=guided.as_canonical(),
            retrieval_profile=command.retrieval_profile or {},
            missing_data=["evidência citável"],
        )
        session.add(stub)
        session.flush()
        _remember(
            session,
            organization_id=organization_id,
            idempotency_key=idempotency_key,
            command="recipe.ai.propose",
            payload=digest_payload,
            resource_type="ai_proposal",
            resource_id=stub.id,
            actor_user_id=principal.user_id,
        )
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_user_id=principal.user_id,
                event_type="recipe_ai_grounding_insufficient",
                aggregate_type="ai_proposal",
                aggregate_id=stub.id,
                payload={"intent": guided.intent},
            )
        )
        session.flush()
        return stub
    if result.proposal is None:
        raise _public_error(OrchestrationError(result.error_code or "proposta_invalida"))
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="recipe.ai.propose",
        payload=digest_payload,
        resource_type="ai_proposal",
        resource_id=result.proposal.id,
        actor_user_id=principal.user_id,
    )
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            event_type="recipe_ai_proposed",
            aggregate_type="ai_proposal",
            aggregate_id=result.proposal.id,
            payload={"intent": guided.intent, "published": False},
        )
    )
    return result.proposal


def list_proposals(session: Session, principal: Principal) -> list[AiProposal]:
    if not (
        PERMISSION_RECIPE_AI_PROPOSE in principal.permissions
        or PERMISSION_RECIPE_AI_REVIEW in principal.permissions
        or PERMISSION_RECIPE_AI_MATERIALIZE in principal.permissions
    ):
        raise ValidationError("permissao_negada")
    organization_id = _org(principal)
    return list(
        session.scalars(
            select(AiProposal)
            .where(AiProposal.organization_id == organization_id)
            .order_by(AiProposal.created_at.desc())
        )
    )


def get_proposal(session: Session, principal: Principal, proposal_id: UUID) -> AiProposal:
    if not (
        PERMISSION_RECIPE_AI_PROPOSE in principal.permissions
        or PERMISSION_RECIPE_AI_REVIEW in principal.permissions
        or PERMISSION_RECIPE_AI_MATERIALIZE in principal.permissions
    ):
        raise ValidationError("permissao_negada")
    return _proposal(session, _org(principal), proposal_id)


def review_changes(
    session: Session,
    principal: Principal,
    proposal_id: UUID,
    *,
    decisions: list[dict],
    expected_version: int | None,
) -> AiProposal:
    require_permission(principal, PERMISSION_RECIPE_AI_REVIEW)
    proposal = _proposal(session, _org(principal), proposal_id)
    _match(proposal, expected_version)
    try:
        decide_changes(
            session, proposal, decisions=decisions, actor_user_id=principal.user_id
        )
    except OrchestrationError as exc:
        raise _public_error(exc) from exc
    return proposal


def decide_proposal(
    session: Session,
    principal: Principal,
    proposal_id: UUID,
    *,
    decision: str,
    notes: str | None,
    confirm: bool,
    idempotency_key: UUID,
    expected_version: int | None,
) -> AiProposal:
    require_permission(principal, PERMISSION_RECIPE_AI_REVIEW)
    organization_id = _org(principal)
    proposal = _proposal(session, organization_id, proposal_id)
    _match(proposal, expected_version)
    if decision == "accepted" and not confirm:
        raise RecipeAiError("confirmacao_obrigatoria")
    payload = {"proposal_id": str(proposal_id), "decision": decision}
    replay = _replay(session, organization_id, idempotency_key, "recipe.ai.review", payload)
    if replay is not None:
        return _proposal(session, organization_id, replay.resource_id)
    try:
        review_proposal(
            session,
            proposal,
            actor_user_id=principal.user_id,
            decision=decision,
            notes=notes,
            materialize=False,
        )
    except OrchestrationError as exc:
        raise _public_error(exc) from exc
    proposal.row_version = int(proposal.row_version or 1) + 1
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="recipe.ai.review",
        payload=payload,
        resource_type="ai_proposal",
        resource_id=proposal.id,
        actor_user_id=principal.user_id,
    )
    return proposal


def materialize_recipe_proposal(
    session: Session,
    principal: Principal,
    proposal_id: UUID,
    *,
    idempotency_key: UUID,
    expected_version: int | None,
) -> AiProposal:
    require_permission(principal, PERMISSION_RECIPE_AI_MATERIALIZE)
    organization_id = _org(principal)
    proposal = _proposal(session, organization_id, proposal_id)
    _match(proposal, expected_version)
    if proposal.status == "materialized" and proposal.materialized_formulation_version_id:
        raise InvalidStateError("proposta_ja_materializada")
    payload = {"proposal_id": str(proposal_id)}
    replay = _replay(session, organization_id, idempotency_key, "recipe.ai.materialize", payload)
    if replay is not None:
        return _proposal(session, organization_id, replay.resource_id)
    try:
        materialize_proposal(session, proposal, actor_user_id=principal.user_id)
    except OrchestrationError as exc:
        raise _public_error(exc) from exc
    proposal.row_version = int(proposal.row_version or 1) + 1
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="recipe.ai.materialize",
        payload=payload,
        resource_type="ai_proposal",
        resource_id=proposal.id,
        actor_user_id=principal.user_id,
    )
    return proposal
