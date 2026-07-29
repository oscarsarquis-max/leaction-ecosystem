import asyncio
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Raiz do projeto + backend no PYTHONPATH (imports cross-package).
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import get_db
from models import PhaseExecution, PipelineRun
from schemas import (
    ApprovePhaseRequest,
    ApprovePhaseResponse,
    AutoApproveRequest,
    AutoApproveResponse,
    DeliverModuleRequest,
    DeliverModuleResponse,
    DraftRequirementsRequest,
    DraftRequirementsResponse,
    GenerateSpecRequest,
    GenerateSpecResponse,
    HealthResponse,
    PhaseStatusRead,
    PipelineHistoryItem,
    PipelineHistoryPhaseSummary,
    PipelineHistoryResponse,
    PipelineStartRequest,
    PipelineStartResponse,
    PipelineStatusResponse,
    ReopenPhaseResponse,
)
from services import state_engine
from services.build_order import locate_module_queue, mark_module_entregue
from services.state_engine import (
    StateEngineError,
    normalize_spec_phases,
    phase_order_from_spec,
)
from services.structured_requirements import (
    PERFIL_ARTEFATO,
    draft_structured_requirements,
)
from services.text_to_spec import generate_pipeline_spec

# Rótulos só como fallback; preferir sempre phase.name da Spec.
PHASE_LABELS = {
    "metodologia": "Metodologia",
    "pesquisa": "Pesquisa",
    "context7_search": "Memoria context7",
    "sintese": "Síntese",
    "generate_prd": "PRD — Requisitos",
    "generate_sdd": "SDD — Design",
    "security_guidelines": "Diretrizes de Segurança",
    "prompt_cursor": "Prompt para IDE",
    "entrega_final": "Entrega final",
    "L1": "Metodologia",
    "L2": "Grounding",
    "L3": "Síntese",
    "L4": "Entrega final",
}

app = FastAPI(
    title="Phanton Orchestrator",
    description="API de Orquestração de Pipeline Multi-Modelo",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/pipeline/draft-requirements", response_model=DraftRequirementsResponse)
async def draft_requirements(
    payload: DraftRequirementsRequest,
) -> DraftRequirementsResponse:
    """Rascunho estruturado de requisitos antes do Spec (Software/SaaS)."""
    prompt = (payload.prompt or "").strip()
    if len(prompt) < 8:
        raise HTTPException(
            status_code=400,
            detail="Descreva o pedido com um pouco mais de detalhe (mín. 8 caracteres).",
        )

    try:
        structured, model = await asyncio.to_thread(
            draft_structured_requirements, prompt
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao rascunhar requisitos: {exc}",
        ) from exc

    skip_panel = structured.get("perfil_sugerido") == PERFIL_ARTEFATO
    return DraftRequirementsResponse(
        structured_requirements=structured,
        model=model,
        skip_panel=skip_panel,
    )


@app.post("/api/pipeline/generate-spec", response_model=GenerateSpecResponse)
async def generate_spec(payload: GenerateSpecRequest) -> GenerateSpecResponse:
    """Text-to-Spec: NL → Pipeline Spec JSON (revisão humana antes do start)."""
    prompt = (payload.prompt or "").strip()
    if len(prompt) < 8:
        raise HTTPException(
            status_code=400,
            detail="Descreva o pipeline com um pouco mais de detalhe (mín. 8 caracteres).",
        )

    structured = payload.structured_requirements
    try:
        spec, model = await asyncio.to_thread(
            generate_pipeline_spec, prompt, structured
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao gerar Pipeline Spec: {exc}",
        ) from exc

    return GenerateSpecResponse(spec=spec, model=model)


def _run_title(spec: dict) -> str:
    if not isinstance(spec, dict):
        return "Pipeline"
    for key in ("name", "description", "user_prompt", "pedido"):
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            text = " ".join(value.strip().split())
            return text[:96] + ("…" if len(text) > 96 else "")
    return "Pipeline"


def _phase_display_name(spec_dict: dict, phase_id: str) -> str:
    cfg = (spec_dict.get("phases") or {}).get(phase_id) if isinstance(spec_dict.get("phases"), dict) else None
    if isinstance(cfg, dict) and cfg.get("name"):
        return str(cfg["name"])
    return PHASE_LABELS.get(phase_id, phase_id.replace("_", " ").title())


@app.get("/api/pipeline", response_model=PipelineHistoryResponse)
def list_pipeline_history(
    limit: int = 40,
    db: Session = Depends(get_db),
) -> PipelineHistoryResponse:
    """Histórico de runs persistidos — fases e artefatos recuperáveis via GET /{run_id}."""
    safe_limit = max(1, min(int(limit or 40), 100))
    runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    total = db.query(PipelineRun).count()

    items: list[PipelineHistoryItem] = []
    for run in runs:
        spec_dict = run.spec if isinstance(run.spec, dict) else dict(run.spec or {})
        executions = (
            db.query(PhaseExecution)
            .filter(PhaseExecution.run_id == run.id)
            .order_by(PhaseExecution.id.asc())
            .all()
        )
        latest_by_phase: dict[str, PhaseExecution] = {}
        for execution in executions:
            latest_by_phase[execution.phase_id] = execution

        plan_ids = phase_order_from_spec(spec_dict)
        for phase_id in latest_by_phase:
            if phase_id not in plan_ids:
                plan_ids.append(phase_id)

        phase_summaries: list[PipelineHistoryPhaseSummary] = []
        approved_count = 0
        for phase_id in plan_ids:
            execution = latest_by_phase.get(phase_id)
            status = execution.status if execution else "PENDING"
            if status == "APPROVED":
                approved_count += 1
            phase_summaries.append(
                PipelineHistoryPhaseSummary(
                    phase_id=phase_id,
                    name=_phase_display_name(spec_dict, phase_id),
                    status=status,
                    has_artifact=bool(execution and execution.artifact_data is not None),
                )
            )

        description = None
        if isinstance(spec_dict.get("description"), str):
            description = spec_dict["description"].strip()[:240] or None
        elif isinstance(spec_dict.get("user_prompt"), str):
            description = spec_dict["user_prompt"].strip()[:240] or None

        items.append(
            PipelineHistoryItem(
                run_id=run.id,
                status=run.status,
                title=_run_title(spec_dict),
                description=description,
                created_at=run.created_at,
                updated_at=run.updated_at,
                phase_count=len(plan_ids),
                approved_count=approved_count,
                phases=phase_summaries,
            )
        )

    return PipelineHistoryResponse(items=items, total=total)


@app.get("/api/pipeline/{run_id}", response_model=PipelineStatusResponse)
def get_pipeline_status(
    run_id: str,
    db: Session = Depends(get_db),
) -> PipelineStatusResponse:
    try:
        run_uuid = UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="run_id inválido") from exc

    run = db.get(PipelineRun, run_uuid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run não encontrado: {run_id}")

    executions = (
        db.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run.id)
        .order_by(PhaseExecution.id.asc())
        .all()
    )

    # Última execução por phase_id (lista ordenada por criação/ID)
    latest_by_phase: dict[str, PhaseExecution] = {}
    for execution in executions:
        latest_by_phase[execution.phase_id] = execution

    spec_dict = run.spec if isinstance(run.spec, dict) else dict(run.spec or {})
    plan_ids = phase_order_from_spec(spec_dict)
    for phase_id in latest_by_phase:
        if phase_id not in plan_ids:
            plan_ids.append(phase_id)

    phases: list[PhaseStatusRead] = []
    for phase_id in plan_ids:
        execution = latest_by_phase.get(phase_id)
        display_name = _phase_display_name(spec_dict, phase_id)

        phases.append(
            PhaseStatusRead(
                id=execution.id if execution else None,
                phase_id=phase_id,
                name=display_name,
                status=execution.status if execution else "PENDING",
                artifact_data=execution.artifact_data if execution else None,
                approver=execution.approver if execution else None,
                comments=execution.comments if execution else None,
                task_token=execution.task_token if execution else None,
            )
        )

    return PipelineStatusResponse(
        run_id=run.id,
        status=run.status,
        spec=run.spec if isinstance(run.spec, dict) else dict(run.spec),
        created_at=run.created_at,
        updated_at=run.updated_at,
        phases=phases,
    )

@app.post("/api/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(
    payload: PipelineStartRequest,
    db: Session = Depends(get_db),
) -> PipelineStartResponse:
    # phases chega como dict (chave = id da fase); extra fields (L2_busca etc.) são preservados.
    spec_dict = payload.spec.model_dump(mode="python")
    if not isinstance(spec_dict.get("phases"), dict):
        spec_dict["phases"] = {}
    if not spec_dict.get("name"):
        spec_dict["name"] = spec_dict.get("description") or "pipeline"
    # Ordena phases pela Spec (`order`) e normaliza types/capabilities.
    spec_dict = normalize_spec_phases(spec_dict)

    run = PipelineRun(
        id=uuid4(),
        spec=spec_dict,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        result = await state_engine.start_pipeline(db, run.id, spec_dict)
    except StateEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao iniciar pipeline: {exc}") from exc

    # trigger_phase devolve phase_id; se auto-aprovou, approve_phase devolve
    # approved_phase_id (+ next_phase com a fase atual aguardando).
    phase_id = result.get("phase_id") or result.get("approved_phase_id")
    task_token = result.get("task_token")
    artifact = result.get("artifact_data")
    next_phase = result.get("next_phase")
    if isinstance(next_phase, dict):
        phase_id = next_phase.get("phase_id") or phase_id
        task_token = next_phase.get("task_token") or task_token
        artifact = next_phase.get("artifact_data") or artifact
        # Encadeamento profundo de auto-aprovações: desce até a ponta.
        cursor = next_phase.get("next_phase")
        while isinstance(cursor, dict):
            phase_id = cursor.get("phase_id") or cursor.get("approved_phase_id") or phase_id
            task_token = cursor.get("task_token") or task_token
            artifact = cursor.get("artifact_data") or artifact
            if cursor.get("status") == "AWAITING_APPROVAL":
                break
            cursor = cursor.get("next_phase")

    return PipelineStartResponse(
        run_id=run.id,
        status=result["status"],
        phase_id=str(phase_id or ""),
        task_token=task_token,
        artifact_data=artifact,
    )


@app.patch("/api/pipeline/{run_id}/auto-approve", response_model=AutoApproveResponse)
def set_pipeline_auto_approve(
    run_id: UUID,
    payload: AutoApproveRequest,
    db: Session = Depends(get_db),
) -> AutoApproveResponse:
    """Atualiza o switch de auto-aprovação no Spec do run (fases futuras)."""
    run = db.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run não encontrado")
    spec = dict(run.spec) if isinstance(run.spec, dict) else {}
    spec["auto_approve"] = bool(payload.auto_approve)
    run.spec = spec
    db.add(run)
    db.commit()
    return AutoApproveResponse(run_id=run_id, auto_approve=bool(payload.auto_approve))


@app.post(
    "/api/pipeline/{run_id}/phases/{phase_id}/reopen",
    response_model=ReopenPhaseResponse,
)
async def reopen_pipeline_phase(
    run_id: UUID,
    phase_id: str,
    db: Session = Depends(get_db),
) -> ReopenPhaseResponse:
    """Reabre fase auto-aprovada para revisão humana (remove fases posteriores)."""
    try:
        result = await state_engine.reopen_auto_approved_phase(db, run_id, phase_id)
    except StateEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Falha ao reabrir fase: {exc}"
        ) from exc
    return ReopenPhaseResponse(**result)


@app.post("/api/pipeline/approve/{task_token}", response_model=ApprovePhaseResponse)
async def approve_pipeline_phase(
    task_token: str,
    payload: Optional[ApprovePhaseRequest] = None,
    db: Session = Depends(get_db),
) -> ApprovePhaseResponse:
    body = payload or ApprovePhaseRequest()
    try:
        result = await state_engine.approve_phase(
            db,
            task_token,
            modified_artifact=body.modified_artifact,
            approver=body.approver,
            comments=body.comments,
        )
    except StateEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao aprovar fase: {exc}") from exc

    next_phase = result.get("next_phase")
    task_token_out = None
    if isinstance(next_phase, dict):
        task_token_out = next_phase.get("task_token")
    else:
        task_token_out = result.get("task_token")

    return ApprovePhaseResponse(
        run_id=result["run_id"],
        approved_phase_id=result["approved_phase_id"],
        status=result["status"],
        next_phase=next_phase,
        task_token=task_token_out,
        artifact_data=result.get("artifact_data"),
    )


@app.post(
    "/api/pipeline/{run_id}/phases/{phase_id}/modules/deliver",
    response_model=DeliverModuleResponse,
)
def deliver_prompt_cursor_module(
    run_id: UUID,
    phase_id: str,
    payload: DeliverModuleRequest,
    db: Session = Depends(get_db),
) -> DeliverModuleResponse:
    """Marca módulo da fila como entregue e libera próximos elegíveis."""
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run não encontrado")

    phase = (
        db.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_id,
            PhaseExecution.phase_id == phase_id,
        )
        .order_by(PhaseExecution.id.desc())
        .first()
    )
    if not phase or not isinstance(phase.artifact_data, dict):
        raise HTTPException(
            status_code=404,
            detail=f"Fase '{phase_id}' sem artefato para este run",
        )

    artifact = dict(phase.artifact_data)
    try:
        container, queue = locate_module_queue(artifact)
        updated_queue = mark_module_entregue(queue, payload.modulo)
        container["module_prompts"] = updated_queue
        first_liberado = next(
            (q for q in updated_queue if q.get("status") == "liberado"),
            None,
        )
        if first_liberado and first_liberado.get("prompt"):
            container["cursor_prompt"] = first_liberado["prompt"]

        # Mantém envelope externo e nested artifact_data sincronizados
        artifact["module_prompts"] = updated_queue
        if first_liberado and first_liberado.get("prompt"):
            artifact["cursor_prompt"] = first_liberado["prompt"]
        nested = artifact.get("artifact_data")
        if isinstance(nested, dict):
            nested = dict(nested)
            nested["module_prompts"] = updated_queue
            if first_liberado and first_liberado.get("prompt"):
                nested["cursor_prompt"] = first_liberado["prompt"]
            artifact["artifact_data"] = nested
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    phase.artifact_data = artifact
    db.add(phase)
    db.commit()
    db.refresh(phase)

    return DeliverModuleResponse(
        run_id=run_id,
        phase_id=phase_id,
        modulo=payload.modulo,
        artifact_data=phase.artifact_data or {},
        module_prompts=updated_queue,
    )
