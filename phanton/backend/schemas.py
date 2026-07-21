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
    Types: methodology | research | synthesize | prompt.
    """

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    phases: dict[str, PhaseConfig | dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRunCreate(BaseModel):
    spec: PipelineSpec
    status: str = "pending"


class PipelineRunRead(BaseModel):
    id: UUID
    spec: PipelineSpec | dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

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


class GenerateSpecResponse(BaseModel):
    """Pipeline Spec gerada a partir de linguagem natural (revisão humana antes do start)."""

    model_config = ConfigDict(extra="allow")

    spec: dict[str, Any]
    model: Optional[str] = None


class PipelineStartRequest(BaseModel):
    """Payload de POST /api/pipeline/start."""

    model_config = ConfigDict(extra="allow")

    spec: PipelineSpec


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
