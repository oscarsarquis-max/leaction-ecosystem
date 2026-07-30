"""Identidade projeto+versão, aceitação e pipelines substitutos (pós-aceitação)."""

from __future__ import annotations

import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from services.phanton_improvements import (  # noqa: E402
    create_proposal_from_retorno,
)
from services.retorno_dual_vision import (  # noqa: E402
    resolve_phanton_improvement_proposal,
)
from models import PhaseExecution, PipelineRun  # noqa: E402

STATUS_COMPLETED = "COMPLETED"
STATUS_ACCEPTED = "ACCEPTED"
ACCEPTANCE_OPEN = "open"
ACCEPTANCE_ACCEPTED = "accepted"

LINEAGE_RETORNO = "retorno"
LINEAGE_EVOLUCAO = "evolucao"


class ProjectVersioningError(Exception):
    """Erro de domínio de projeto/versão/aceitação."""


def slugify_project_key(name: str, *, max_len: int = 80) -> str:
    """Normaliza nome do projeto em chave estável (slug ASCII)."""
    text = (name or "").strip()
    if not text:
        return "projeto"
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    if not slug:
        slug = "projeto"
    return slug[:max_len].rstrip("-") or "projeto"


def normalize_version(version: Any) -> str:
    raw = str(version or "1.0").strip()
    return raw or "1.0"


def bump_version(version: str) -> str:
    """Incrementa o menor componente numérico (1.0 → 1.1, 1.9 → 1.10, 2 → 2.1)."""
    parts = re.findall(r"\d+", normalize_version(version))
    if not parts:
        return "1.1"
    nums = [int(p) for p in parts]
    if len(nums) == 1:
        nums.append(1)
    else:
        nums[-1] += 1
    return ".".join(str(n) for n in nums)


def project_name_from_spec(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict):
        return "Projeto"
    for key in ("name", "description", "user_prompt", "pedido"):
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.strip().split())[:120]
    return "Projeto"


def is_accepted(run: PipelineRun) -> bool:
    if (run.acceptance_status or "").strip().lower() == ACCEPTANCE_ACCEPTED:
        return True
    return (run.status or "").strip().upper() == STATUS_ACCEPTED


def assert_run_mutable(run: PipelineRun) -> None:
    """Bloqueia mutação in-place após aceitação (resultado final imutável)."""
    if is_accepted(run):
        raise ProjectVersioningError(
            "Projeto aceito — resultado imutável. Use retorno ou evolução "
            "para criar um pipeline substituto versionado."
        )


def ensure_identity_on_spec(
    spec: dict[str, Any],
    *,
    project_name: Optional[str] = None,
    project_key: Optional[str] = None,
    version: Optional[str] = None,
) -> dict[str, Any]:
    """Garante name/version/project_key no Spec (mutável)."""
    out = dict(spec) if isinstance(spec, dict) else {}
    name = (project_name or out.get("name") or project_name_from_spec(out)).strip()
    out["name"] = name
    out["version"] = normalize_version(version or out.get("version") or "1.0")
    key = project_key or out.get("project_key") or slugify_project_key(name)
    out["project_key"] = slugify_project_key(str(key))
    return out


def sync_run_identity(run: PipelineRun, spec: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Alinha colunas do run com o Spec."""
    spec_dict = ensure_identity_on_spec(
        spec if isinstance(spec, dict) else (run.spec if isinstance(run.spec, dict) else {})
    )
    run.spec = spec_dict
    run.project_key = spec_dict["project_key"]
    run.project_name = spec_dict["name"]
    run.version = spec_dict["version"]
    if not run.acceptance_status:
        run.acceptance_status = ACCEPTANCE_OPEN
    return spec_dict


def accept_project(
    db_session: Session,
    run_id: str | UUID,
    *,
    project_name: Optional[str] = None,
) -> dict[str, Any]:
    """Fecha aceitação do projeto completo — congela o resultado."""
    run_uuid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise ProjectVersioningError(f"Pipeline run não encontrado: {run_uuid}")

    if is_accepted(run):
        raise ProjectVersioningError("Projeto já está aceito e imutável")

    if (run.status or "").strip().upper() != STATUS_COMPLETED:
        raise ProjectVersioningError(
            "Só é possível aceitar quando o pipeline estiver COMPLETED "
            f"(status atual: {run.status})"
        )

    spec = ensure_identity_on_spec(
        run.spec if isinstance(run.spec, dict) else {},
        project_name=project_name,
    )
    sync_run_identity(run, spec)
    run.acceptance_status = ACCEPTANCE_ACCEPTED
    run.accepted_at = datetime.utcnow()
    run.status = STATUS_ACCEPTED
    run.updated_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(run)

    return {
        "run_id": str(run.id),
        "project_key": run.project_key,
        "project_name": run.project_name,
        "version": run.version,
        "status": run.status,
        "acceptance_status": run.acceptance_status,
        "accepted_at": run.accepted_at,
    }


def search_accepted_projects(
    db_session: Session,
    *,
    query: str = "",
    version: Optional[str] = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Busca projetos/versões aceitos por nome, key ou version."""
    safe_limit = max(1, min(int(limit or 40), 100))
    q = (
        db_session.query(PipelineRun)
        .filter(PipelineRun.acceptance_status == ACCEPTANCE_ACCEPTED)
        .order_by(PipelineRun.accepted_at.desc().nullslast(), PipelineRun.created_at.desc())
    )

    needle = (query or "").strip()
    if needle:
        like = f"%{needle}%"
        q = q.filter(
            or_(
                PipelineRun.project_key.ilike(like),
                PipelineRun.project_name.ilike(like),
                PipelineRun.version.ilike(like),
            )
        )

    if version and str(version).strip():
        q = q.filter(PipelineRun.version == normalize_version(version))

    rows = q.limit(safe_limit).all()
    items: list[dict[str, Any]] = []
    for run in rows:
        items.append(
            {
                "run_id": str(run.id),
                "project_key": run.project_key or "",
                "project_name": run.project_name or project_name_from_spec(
                    run.spec if isinstance(run.spec, dict) else {}
                ),
                "version": run.version or normalize_version(
                    (run.spec or {}).get("version") if isinstance(run.spec, dict) else "1.0"
                ),
                "status": run.status,
                "acceptance_status": run.acceptance_status,
                "accepted_at": run.accepted_at,
                "created_at": run.created_at,
                "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
                "lineage_kind": run.lineage_kind,
            }
        )
    return items


def _artifact_digest(db_session: Session, run_id: UUID, *, max_chars: int = 6000) -> str:
    """Resumo textual dos artefatos aprovados para alimentar reanálise."""
    executions = (
        db_session.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_id)
        .order_by(PhaseExecution.id.asc())
        .all()
    )
    chunks: list[str] = []
    used = 0
    for execution in executions:
        if execution.status not in ("APPROVED", "AWAITING_APPROVAL"):
            continue
        art = execution.artifact_data if isinstance(execution.artifact_data, dict) else {}
        payload = art.get("artifact_data") if isinstance(art.get("artifact_data"), dict) else art
        if not isinstance(payload, dict):
            continue
        # Campos mais úteis primeiro
        for key in (
            "prd_markdown",
            "sdd_markdown",
            "security_markdown",
            "cursor_prompt",
            "sintese",
            "summary",
            "markdown",
            "html",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                piece = f"### {execution.phase_id} · {key}\n{value.strip()}\n"
                if used + len(piece) > max_chars:
                    remain = max_chars - used
                    if remain > 200:
                        chunks.append(piece[:remain] + "\n…(truncado)")
                        used = max_chars
                    return "\n".join(chunks)
                chunks.append(piece)
                used += len(piece)
                break
        else:
            # Fallback: JSON curto
            import json

            raw = json.dumps(payload, ensure_ascii=False)[:800]
            piece = f"### {execution.phase_id}\n{raw}\n"
            if used + len(piece) > max_chars:
                break
            chunks.append(piece)
            used += len(piece)

    return "\n".join(chunks) if chunks else "(sem artefatos textuais resumíveis)"


def build_reanalysis_prompt(
    *,
    project_name: str,
    version: str,
    next_version: str,
    kind: str,
    user_input: str,
    prior_prompt: str,
    artifact_digest: str,
) -> str:
    kind_label = "retorno do implementador" if kind == LINEAGE_RETORNO else "pedido de evolução"
    return (
        f"Reanálise de projeto aceito para gerar um pipeline SUBSTITUTO versionado.\n"
        f"Projeto: {project_name}\n"
        f"Versão aceita (imutável): {version}\n"
        f"Nova versão a criar: {next_version}\n"
        f"Tipo: {kind_label}\n\n"
        f"Pedido original (referência):\n{prior_prompt.strip() or '(não registrado)'}\n\n"
        f"Resumo dos artefatos da versão aceita:\n{artifact_digest}\n\n"
        f"Entrada desta reanálise ({kind_label}):\n{user_input.strip()}\n\n"
        "Gere um Pipeline Spec completo alinhado ao estado desejado após essa entrada. "
        "Mantenha o mesmo nome de produto quando fizer sentido. "
        "A versão no Spec deve ser exatamente a nova versão indicada acima."
    )


def create_substitute_draft(
    db_session: Session,
    source_run_id: str | UUID,
    *,
    kind: str,
    user_input: str,
    generate_spec_fn,
) -> dict[str, Any]:
    """Reanalisa (retorno ou evolução) e cria run pendente substituto — sem mutar o aceito."""
    if kind not in (LINEAGE_RETORNO, LINEAGE_EVOLUCAO):
        raise ProjectVersioningError(f"lineage_kind inválido: {kind}")

    text = (user_input or "").strip()
    if len(text) < 20:
        raise ProjectVersioningError(
            "Descreva com mais detalhe (mín. 20 caracteres) para a reanálise."
        )

    run_uuid = source_run_id if isinstance(source_run_id, UUID) else UUID(str(source_run_id))
    source = db_session.get(PipelineRun, run_uuid)
    if source is None:
        raise ProjectVersioningError(f"Pipeline run não encontrado: {run_uuid}")
    if not is_accepted(source):
        raise ProjectVersioningError(
            "Retorno e evolução só ficam disponíveis após a aceitação do projeto."
        )

    # Retorno: dupla visão — só a metade pipeline alimenta o Spec substituto.
    pipeline_input = text
    dual = None
    if kind == LINEAGE_RETORNO:
        dual = resolve_phanton_improvement_proposal(text, use_llm_fallback=True)
        pipeline_input = (dual.get("pipeline_section") or text).strip() or text

    source_spec = source.spec if isinstance(source.spec, dict) else {}
    source_spec = ensure_identity_on_spec(source_spec)
    next_version = bump_version(source.version or source_spec.get("version") or "1.0")
    project_name = source.project_name or source_spec.get("name") or "Projeto"
    project_key = source.project_key or slugify_project_key(project_name)

    prior_prompt = ""
    for key in ("user_prompt", "description", "pedido"):
        value = source_spec.get(key)
        if isinstance(value, str) and value.strip():
            prior_prompt = value.strip()
            break

    digest = _artifact_digest(db_session, source.id)
    prompt = build_reanalysis_prompt(
        project_name=project_name,
        version=normalize_version(source.version or "1.0"),
        next_version=next_version,
        kind=kind,
        user_input=pipeline_input,
        prior_prompt=prior_prompt,
        artifact_digest=digest,
    )

    structured = source_spec.get("structured_requirements")
    if not isinstance(structured, dict):
        structured = None

    new_spec, model = generate_spec_fn(prompt, structured)
    if not isinstance(new_spec, dict):
        raise ProjectVersioningError("Reanálise não retornou um Spec válido")

    new_spec = ensure_identity_on_spec(
        new_spec,
        project_name=project_name,
        project_key=project_key,
        version=next_version,
    )
    new_spec["user_prompt"] = pipeline_input
    new_spec["description"] = (
        f"{project_name} v{next_version} ({'retorno' if kind == LINEAGE_RETORNO else 'evolução'})"
    )
    new_spec["lineage"] = {
        "kind": kind,
        "parent_run_id": str(source.id),
        "parent_version": normalize_version(source.version or "1.0"),
        "source_input": text,
        "pipeline_input": pipeline_input,
    }
    if structured:
        new_spec["structured_requirements"] = structured

    # Arquiva entrada no run aceito (sem alterar artefatos)
    if kind == LINEAGE_RETORNO:
        source.retorno_markdown = text
    source.updated_at = datetime.utcnow()

    child = PipelineRun(
        id=uuid4(),
        spec=new_spec,
        status="pending",
        project_key=project_key,
        project_name=project_name,
        version=next_version,
        acceptance_status=ACCEPTANCE_OPEN,
        parent_run_id=source.id,
        lineage_kind=kind,
        retorno_markdown=text if kind == LINEAGE_RETORNO else None,
    )
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)

    phanton_improvement = None
    if kind == LINEAGE_RETORNO:
        # Evita segundo LLM se já resolvemos no início; reusa extract local + create
        phanton_improvement = create_proposal_from_retorno(
            db_session,
            source_run_id=source.id,
            substitute_run_id=child.id,
            full_retorno=text,
            use_llm_fallback=True,
            resolved=dual,
        )

    return {
        "source_run_id": str(source.id),
        "run_id": str(child.id),
        "project_key": project_key,
        "project_name": project_name,
        "version": next_version,
        "parent_version": normalize_version(source.version or "1.0"),
        "lineage_kind": kind,
        "status": child.status,
        "spec": new_spec,
        "model": model,
        "phanton_improvement": phanton_improvement,
    }
