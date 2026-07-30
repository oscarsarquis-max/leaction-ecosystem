from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider: Optional[str] = None
    model: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)


class PhaseConfig(BaseModel):
    """Detalhes de uma fase no mapa `phases` (chave = id da fase)."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    model: Optional[ModelConfig] = None
    depends_on: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class PipelineSpec(BaseModel):
    """Especificação JSON do pipeline multi-modelo.

    `phases` é um dicionário: chave = id livre da fase (ex.: "pesquisa_casos"),
    valor = configuração (name, type, order, descricao, depends_on…).
    Types: methodology | research | context7_search | synthesize | generate_prd |
    generate_sdd | security_guidelines | prompt_cursor | task_breakdown | prompt
    (aliases: context7, prd, sdd, security, delivery, html, ide_prompt,
    linear_export, jira_export).
    """

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    phases: dict[str, PhaseConfig | dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Quando True, fases com quality_score >= 80 (fora de ALWAYS_HUMAN) avançam sozinhas.
    auto_approve: bool = False
    # Lacunas de contexto no pedido (informativo — não bloqueia start).
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    # Rascunho 29148 revisado pelo humano (quando perfil software_saas).
    structured_requirements: Optional[dict[str, Any]] = None


class PipelineRunCreate(BaseModel):
    spec: PipelineSpec
    status: str = "pending"


class PipelineRunRead(BaseModel):
    id: UUID
    spec: PipelineSpec | dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    project_key: Optional[str] = None
    project_name: Optional[str] = None
    version: Optional[str] = None
    acceptance_status: str = "open"
    accepted_at: Optional[datetime] = None
    parent_run_id: Optional[UUID] = None
    lineage_kind: Optional[str] = None

    model_config = {"from_attributes": True}


class PhaseExecutionCreate(BaseModel):
    run_id: UUID
    phase_id: str
    status: str = "pending"
    artifact_data: Optional[dict[str, Any]] = None
    approver: Optional[str] = None
    comments: Optional[str] = None
    task_token: Optional[str] = None


class PhaseExecutionRead(BaseModel):
    id: UUID
    run_id: UUID
    phase_id: str
    status: str
    artifact_data: Optional[dict[str, Any]] = None
    approver: Optional[str] = None
    comments: Optional[str] = None
    task_token: Optional[str] = None

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    service: str = "phanton-backend"


class GenerateSpecRequest(BaseModel):
    prompt: str
    structured_requirements: Optional[dict[str, Any]] = None


class GenerateSpecResponse(BaseModel):
    """Pipeline Spec gerada a partir de linguagem natural (revisão humana antes do start)."""

    model_config = ConfigDict(extra="allow")

    spec: dict[str, Any]
    model: Optional[str] = None


class DraftRequirementsRequest(BaseModel):
    prompt: str


class DraftRequirementsResponse(BaseModel):
    """Rascunho estruturado de requisitos (ISO/IEC/IEEE 29148 simplificado)."""

    model_config = ConfigDict(extra="allow")

    structured_requirements: dict[str, Any]
    model: Optional[str] = None
    skip_panel: bool = False


class PipelineStartRequest(BaseModel):
    """Payload de POST /api/pipeline/start."""

    model_config = ConfigDict(extra="allow")

    spec: PipelineSpec
    # Quando informado, inicia um run `pending` já criado (ex.: substituto pós-aceitação).
    existing_run_id: Optional[UUID] = None


class PipelineStartResponse(BaseModel):
    run_id: UUID
    status: str
    phase_id: str
    task_token: Optional[str] = None
    artifact_data: Optional[dict[str, Any]] = None


class ApprovePhaseRequest(BaseModel):
    modified_artifact: Optional[dict[str, Any]] = None
    approver: Optional[str] = None
    comments: Optional[str] = None


class ApprovePhaseResponse(BaseModel):
    run_id: UUID
    approved_phase_id: str
    status: str
    next_phase: Optional[dict[str, Any]] = None
    task_token: Optional[str] = None
    artifact_data: Optional[dict[str, Any]] = None


class AutoApproveRequest(BaseModel):
    """Liga/desliga auto-aprovação por qualidade no run (afeta fases futuras)."""

    auto_approve: bool = False


class AutoApproveResponse(BaseModel):
    run_id: UUID
    auto_approve: bool


class ReopenPhaseResponse(BaseModel):
    run_id: UUID
    phase_id: str
    status: str
    task_token: Optional[str] = None
    artifact_data: Optional[dict[str, Any]] = None


class DeliverModuleRequest(BaseModel):
    """Marca um módulo da fila prompt_cursor como entregue."""

    modulo: str


class DeliverModuleResponse(BaseModel):
    run_id: UUID
    phase_id: str
    modulo: str
    artifact_data: dict[str, Any]
    module_prompts: list[dict[str, Any]] = Field(default_factory=list)


class PhaseStatusRead(BaseModel):
    id: Optional[UUID] = None
    phase_id: str
    name: str
    status: str
    artifact_data: Optional[dict[str, Any]] = None
    approver: Optional[str] = None
    comments: Optional[str] = None
    task_token: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    run_id: UUID
    status: str
    spec: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    phases: list[PhaseStatusRead]
    project_key: Optional[str] = None
    project_name: Optional[str] = None
    version: Optional[str] = None
    acceptance_status: str = "open"
    accepted_at: Optional[datetime] = None
    parent_run_id: Optional[UUID] = None
    lineage_kind: Optional[str] = None
    immutable: bool = False
    can_accept: bool = False


class PipelineHistoryPhaseSummary(BaseModel):
    phase_id: str
    name: str
    status: str
    has_artifact: bool = False


class PipelineHistoryItem(BaseModel):
    run_id: UUID
    status: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    phase_count: int = 0
    approved_count: int = 0
    phases: list[PipelineHistoryPhaseSummary] = Field(default_factory=list)
    project_key: Optional[str] = None
    version: Optional[str] = None
    acceptance_status: Optional[str] = None


class PipelineHistoryResponse(BaseModel):
    items: list[PipelineHistoryItem]
    total: int


class AcceptProjectRequest(BaseModel):
    project_name: Optional[str] = None


class AcceptProjectResponse(BaseModel):
    run_id: UUID
    project_key: str
    project_name: str
    version: str
    status: str
    acceptance_status: str
    accepted_at: Optional[datetime] = None


class ProjectSearchItem(BaseModel):
    run_id: UUID
    project_key: str
    project_name: str
    version: str
    status: str
    acceptance_status: str
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    parent_run_id: Optional[UUID] = None
    lineage_kind: Optional[str] = None


class ProjectSearchResponse(BaseModel):
    items: list[ProjectSearchItem]
    total: int


class RetornoRequest(BaseModel):
    content: str


class EvolveRequest(BaseModel):
    request: str


class PhantonImprovementRead(BaseModel):
    id: UUID
    source_run_id: Optional[UUID] = None
    substitute_run_id: Optional[UUID] = None
    title: str
    summary: str
    items: list[Any] = Field(default_factory=list)
    status: str
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None


class PhantonImprovementDecisionRequest(BaseModel):
    decision: str  # aceitar | rejeitar | accept | reject


class PhantonImprovementDecisionResponse(BaseModel):
    id: UUID
    status: str
    title: str
    summary: str
    decided_at: Optional[datetime] = None


class SubstitutePipelineResponse(BaseModel):
    source_run_id: UUID
    run_id: UUID
    project_key: str
    project_name: str
    version: str
    parent_version: str
    lineage_kind: str
    status: str
    spec: dict[str, Any]
    model: Optional[str] = None
    phanton_improvement: Optional[PhantonImprovementRead] = None


class LinearExportResponse(BaseModel):
    """Resumo da exportação task_breakdown → Linear."""

    run_id: UUID
    phase_id: str
    summary: str
    project: dict[str, Any] = Field(default_factory=dict)
    issues_created: int = 0
    epics_count: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)