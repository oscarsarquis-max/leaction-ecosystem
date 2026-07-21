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
    GenerateSpecRequest,
    GenerateSpecResponse,
    HealthResponse,
    PhaseStatusRead,
    PipelineStartRequest,
    PipelineStartResponse,
    PipelineStatusResponse,
)
from services import state_engine
from services.state_engine import (
    StateEngineError,
    normalize_spec_phases,
    phase_order_from_spec,
)
from services.text_to_spec import generate_pipeline_spec

# Rótulos só como fallback; preferir sempre phase.name da Spec.
PHASE_LABELS = {
    "metodologia": "Metodologia",
    "pesquisa": "Pesquisa",
    "sintese": "Síntese",
    "prompt_cursor": "Prompt para o Cursor",
    "L1": "Metodologia",
    "L2": "Grounding",
    "L3": "Síntese",
    "L4": "Prompt para o Cursor",
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


@app.post("/api/pipeline/generate-spec", response_model=GenerateSpecResponse)
async def generate_spec(payload: GenerateSpecRequest) -> GenerateSpecResponse:
    """Text-to-Spec: NL → Pipeline Spec JSON (revisão humana antes do start)."""
    prompt = (payload.prompt or "").strip()
    if len(prompt) < 8:
        raise HTTPException(
            status_code=400,
            detail="Descreva o pipeline com um pouco mais de detalhe (mín. 8 caracteres).",
        )

    try:
        spec, model = await asyncio.to_thread(generate_pipeline_spec, prompt)
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
        cfg = (spec_dict.get("phases") or {}).get(phase_id) if isinstance(spec_dict.get("phases"), dict) else None
        if isinstance(cfg, dict) and cfg.get("name"):
            display_name = str(cfg["name"])
        else:
            display_name = PHASE_LABELS.get(phase_id, phase_id.replace("_", " ").title())

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

    return PipelineStartResponse(
        run_id=run.id,
        status=result["status"],
        phase_id=result["phase_id"],
        task_token=result.get("task_token"),
        artifact_data=result.get("artifact_data"),
    )


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
