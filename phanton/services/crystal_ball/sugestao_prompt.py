"""Fase sugestao_prompt_geral — recomendação de template (somente texto copiável).

Nunca escreve em sistemas externos. Fecha um ciclo_melhoria com nota agregada.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.crystal_ball.campo_compare import compare_literal_fields
from services.crystal_ball.corpora import get_corpus
from services.crystal_ball.models import (
    CrystalCicloMelhoria,
    CrystalShadowPhase,
    CrystalShadowRun,
    CrystalSugestaoArtifact,
)
from services.crystal_ball.passos_compare import extract_passos_from_artifact

PHASE_ENTREGA = "entrega_final"
PHASE_SYNTHESIZE = "synthesize"
PHASE_CONTEXT7 = "context7_mativas"


class SugestaoPromptError(Exception):
    pass


def _latest_phase(
    db: Session, shadow_id: UUID, phase_id: str
) -> Optional[dict[str, Any]]:
    row = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_id,
            CrystalShadowPhase.phase_id == phase_id,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    if not row or not isinstance(row.artifact_data, dict):
        return None
    return row.artifact_data


def _chave_from_shadow(db: Session, shadow: CrystalShadowRun) -> str:
    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    if spec.get("metodologia"):
        return str(spec["metodologia"])
    c7 = _latest_phase(db, shadow.id, PHASE_CONTEXT7)
    if isinstance(c7, dict):
        return str(
            c7.get("metodologia_encontrada")
            or (c7.get("corpus_registro") or {}).get("metodologia")
            or ""
        )
    return ""


def comparison_for_shadow(
    db: Session,
    shadow: CrystalShadowRun,
    schema_config: dict[str, Any],
) -> dict[str, Any]:
    """Usa comparison guardada no spec, ou recalcula a partir das fases."""
    from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
        lookup_by_chave,
    )

    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    stored = spec.get("comparison")
    if isinstance(stored, dict) and (
        stored.get("nota_por_campo") or stored.get("identical_ratio") is not None
    ):
        out = dict(stored)
        out.setdefault("shadow_run_id", str(shadow.id))
        return out

    chave = _chave_from_shadow(db, shadow)
    registro = lookup_by_chave(schema_config, chave) if chave else None
    if not registro:
        return {
            "identical_ratio": None,
            "nota_agregada": None,
            "nota_por_campo": {},
            "error": "registro do corpus não encontrado para o shadow",
            "chave_valor": chave,
            "shadow_run_id": str(shadow.id),
        }

    gen_art: Any = {}
    row_e = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow.id,
            CrystalShadowPhase.phase_id == PHASE_ENTREGA,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    if row_e and isinstance(row_e.artifact_data, dict):
        gen_art = row_e.artifact_data
        if not extract_passos_from_artifact(gen_art):
            gen_art = {"artifact_data": row_e.artifact_data}

    if not extract_passos_from_artifact(gen_art):
        row_s = (
            db.query(CrystalShadowPhase)
            .filter(
                CrystalShadowPhase.shadow_run_id == shadow.id,
                CrystalShadowPhase.phase_id == PHASE_SYNTHESIZE,
            )
            .order_by(CrystalShadowPhase.created_at.desc())
            .first()
        )
        if row_s and isinstance(row_s.artifact_data, dict):
            gen_art = {"artifact_data": row_s.artifact_data}

    cmp_ = compare_literal_fields(
        generated_artifact=gen_art,
        reference_record=registro,
        schema_config=schema_config,
    )
    cmp_["chave_valor"] = chave
    cmp_["shadow_run_id"] = str(shadow.id)
    return cmp_


def _aggregate(
    comparisons: list[dict[str, Any]],
) -> tuple[Optional[float], dict[str, Any], list[str]]:
    ratios: list[float] = []
    field_ratios: dict[str, list[float]] = defaultdict(list)
    evidencias: list[str] = []

    for cmp_ in comparisons:
        r = cmp_.get("nota_agregada")
        if r is None:
            r = cmp_.get("identical_ratio")
        if isinstance(r, (int, float)):
            ratios.append(float(r))
        npc = cmp_.get("nota_por_campo") or {}
        if not isinstance(npc, dict):
            continue
        sid = cmp_.get("shadow_run_id") or "?"
        chave = cmp_.get("chave_valor") or "?"
        for campo, detail in npc.items():
            if not isinstance(detail, dict):
                continue
            # lista_passos: use identical_ratio + subcampos
            fr = detail.get("identical_ratio")
            if isinstance(fr, (int, float)):
                field_ratios[campo].append(float(fr))
            sub = detail.get("subcampos") or {}
            if isinstance(sub, dict):
                for sub_name, sub_d in sub.items():
                    if isinstance(sub_d, dict) and isinstance(
                        sub_d.get("identical_ratio"), (int, float)
                    ):
                        key = f"{campo}.{sub_name}"
                        field_ratios[key].append(float(sub_d["identical_ratio"]))
            # evidence line for zero-fidelity
            if isinstance(fr, (int, float)) and fr == 0.0:
                n_ref = detail.get("n_referencia")
                evidencias.append(
                    f"shadow `{sid}` ({chave}): campo `{campo}` identical_ratio=0"
                    + (f" (n_ref={n_ref})" if n_ref is not None else "")
                )
            elif detail.get("identical") is False:
                evidencias.append(
                    f"shadow `{sid}` ({chave}): campo `{campo}` não idêntico"
                )

    nota_agregada = (sum(ratios) / len(ratios)) if ratios else None
    nota_por_campo: dict[str, Any] = {}
    for campo, vals in field_ratios.items():
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        nota_por_campo[campo] = {
            "identical_ratio_medio": avg,
            "n_simulacoes": len(vals),
            "ratios": vals,
            "sempre_identico": all(v >= 0.999 for v in vals),
            "nunca_identico": all(v <= 0.001 for v in vals),
        }
    return nota_agregada, nota_por_campo, evidencias


def _versao_from_cmp_or_shadow(
    shadow: CrystalShadowRun, cmp_: dict[str, Any]
) -> Optional[str]:
    v = cmp_.get("versao_corpus")
    if isinstance(v, str) and v.strip():
        return v.strip()
    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    v2 = spec.get("versao_corpus")
    if isinstance(v2, str) and v2.strip():
        return v2.strip()
    return None


def _render_markdown(
    *,
    corpus_nome: str,
    aplicacao_origem: str,
    numero_ciclo: int,
    nota_agregada: Optional[float],
    nota_por_campo: dict[str, Any],
    evidencias: list[str],
    prompt_mestre: Optional[str],
    n_sims: int,
    aviso_versoes: Optional[str] = None,
    versoes_shadow: Optional[list[tuple[str, str]]] = None,
) -> str:
    nota_line = (
        f"- Nota agregada (média identical_ratio): **{nota_agregada * 100:.1f}%**"
        if isinstance(nota_agregada, (int, float))
        else "- Nota agregada: **n/d**"
    )
    lines: list[str] = [
        f"# Sugestão de prompt geral — ciclo {numero_ciclo}",
        "",
        "> **Artefato de recomendação.** Não aplica automaticamente nada em "
        "sistemas externos. Copie e cole manualmente onde for usar.",
        "",
        f"- Corpus: **{corpus_nome}**",
        f"- Aplicação de origem: **{aplicacao_origem}**",
        f"- Simulações agregadas: **{n_sims}**",
        nota_line,
        "",
    ]
    if aviso_versoes:
        lines.extend(
            [
                "## ⚠️ Atenção: versões diferentes do corpus",
                "",
                aviso_versoes,
                "",
            ]
        )
        if versoes_shadow:
            lines.append("| Shadow | versao_corpus |")
            lines.append("|--------|---------------|")
            for sid, ver in versoes_shadow:
                short = (ver or "—")[:20] + ("…" if ver and len(ver) > 20 else "")
                lines.append(f"| `{sid}` | `{short}` |")
            lines.append("")
            lines.append(
                "_A nota abaixo **não deve ser lida como evolução confiável** "
                "entre essas simulações._"
            )
            lines.append("")

    lines.extend(
        [
            "## Diagnóstico por campo (campos_copia_literal)",
            "",
        ]
    )
    if not nota_por_campo:
        lines.append("_Sem dados de campo suficientes._")
    else:
        lines.append("| Campo | Média | N | Padrão |")
        lines.append("|-------|-------|---|--------|")
        for campo, d in sorted(nota_por_campo.items()):
            avg = d.get("identical_ratio_medio")
            avg_s = f"{avg * 100:.1f}%" if isinstance(avg, (int, float)) else "—"
            padrao = (
                "sempre idêntico"
                if d.get("sempre_identico")
                else (
                    "nunca idêntico"
                    if d.get("nunca_identico")
                    else "parcial / inconsistente"
                )
            )
            lines.append(
                f"| `{campo}` | {avg_s} | {d.get('n_simulacoes')} | {padrao} |"
            )

    lines.extend(["", "## Recomendações", ""])
    recs: list[str] = []
    for campo, d in sorted(nota_por_campo.items()):
        if d.get("nunca_identico"):
            ratios = d.get("ratios") or []
            fracs = ", ".join(f"{int(r * 100)}%" for r in ratios)
            base = campo.split(".")[-1]
            recs.append(
                f"1. **Mover `{base}` (via `{campo}`) para substituição "
                f"determinística** em vez de instrução de cópia no prompt. "
                f"Evidência: ratios {fracs} nas {d.get('n_simulacoes')} "
                f"simulações — o modelo não reproduz o literal."
            )
        elif d.get("sempre_identico"):
            recs.append(
                f"1. Manter `{campo}` como está — fidelidade estável "
                f"({(d.get('identical_ratio_medio') or 0) * 100:.0f}% médio)."
            )
        else:
            recs.append(
                f"1. Reforçar no prompt mestre a obrigação de cópia literal de "
                f"`{campo}` (hoje parcial: "
                f"{(d.get('identical_ratio_medio') or 0) * 100:.0f}% médio) "
                f"**ou** migrar para substituição determinística se continuar "
                f"instável no próximo ciclo."
            )
    if not recs:
        recs.append("1. Coletar mais simulações com falhas observáveis antes de mudar o template.")
    lines.extend(recs)

    lines.extend(["", "## Evidências citadas", ""])
    if evidencias:
        for e in evidencias[:40]:
            lines.append(f"- {e}")
    else:
        lines.append("- Nenhuma falha total registrada; ver médias na tabela.")

    if prompt_mestre and prompt_mestre.strip():
        lines.extend(
            [
                "",
                "## Prompt mestre de referência (fornecido)",
                "",
                "```",
                prompt_mestre.strip()[:8000],
                "```",
                "",
                "_Revise o bloco acima aplicando as recomendações; o Phanton "
                "não grava essa revisão em lugar nenhum._",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            f"_Ciclo {numero_ciclo} · gerado em {datetime.now(UTC).isoformat()}_",
        ]
    )
    return "\n".join(lines)


def gerar_sugestao_prompt_geral(
    db: Session,
    *,
    corpus_id: UUID | str,
    shadow_run_ids: list[UUID | str],
    prompt_mestre: Optional[str] = None,
) -> dict[str, Any]:
    corpus = get_corpus(db, corpus_id)
    schema = dict(corpus.schema_config or {})
    if len(shadow_run_ids) < 2:
        raise SugestaoPromptError(
            "São necessárias pelo menos 2 simulações (shadow runs) do mesmo corpus"
        )

    comparisons: list[dict[str, Any]] = []
    ids_ok: list[str] = []
    versoes: list[tuple[str, str]] = []
    for raw_id in shadow_run_ids:
        sid = UUID(str(raw_id))
        shadow = db.get(CrystalShadowRun, sid)
        if not shadow:
            raise SugestaoPromptError(f"shadow_run não encontrado: {sid}")
        cmp_ = comparison_for_shadow(db, shadow, schema)
        comparisons.append(cmp_)
        ids_ok.append(str(sid))
        versoes.append((str(sid), _versao_from_cmp_or_shadow(shadow, cmp_) or ""))

    versao_set = {v for _, v in versoes if v}
    aviso_versoes = None
    misturou_versoes = len(versao_set) > 1
    if misturou_versoes:
        aviso_versoes = (
            "Atenção: comparando versões diferentes do corpus. "
            "Os shadows abaixo não compartilham o mesmo `versao_corpus`."
        )
    # Sem hash gravado em alguns shadows legados: avisar se misturar vazio + hash
    if any(not v for _, v in versoes) and any(v for _, v in versoes):
        misturou_versoes = True
        aviso_versoes = (
            "Atenção: alguns shadows não têm `versao_corpus` gravado "
            "(legado) e outros têm — agregação sem garantia de mesma fonte."
        )

    nota_agregada, nota_por_campo, evidencias = _aggregate(comparisons)
    next_n = (
        db.query(func.coalesce(func.max(CrystalCicloMelhoria.numero_ciclo), 0))
        .filter(CrystalCicloMelhoria.corpus_id == corpus.id)
        .scalar()
    )
    numero_ciclo = int(next_n or 0) + 1

    md = _render_markdown(
        corpus_nome=corpus.nome,
        aplicacao_origem=corpus.aplicacao_origem or "Mativas",
        numero_ciclo=numero_ciclo,
        nota_agregada=nota_agregada,
        nota_por_campo=nota_por_campo,
        evidencias=evidencias,
        prompt_mestre=prompt_mestre,
        n_sims=len(ids_ok),
        aviso_versoes=aviso_versoes,
        versoes_shadow=versoes if misturou_versoes else None,
    )

    artifact = CrystalSugestaoArtifact(
        id=uuid.uuid4(),
        corpus_id=corpus.id,
        markdown=md,
        meta={
            "fase": "sugestao_prompt_geral",
            "n_simulacoes": len(ids_ok),
            "shadow_run_ids": ids_ok,
            "somente_copia_manual": True,
            "escreve_sistema_externo": False,
            "versao_corpus_mistas": misturou_versoes,
            "versoes_corpus": {sid: ver for sid, ver in versoes},
            "aplicacao_origem": corpus.aplicacao_origem or "Mativas",
            "comparavel_com_confianca": not misturou_versoes,
        },
    )
    db.add(artifact)
    db.flush()

    ciclo = CrystalCicloMelhoria(
        id=uuid.uuid4(),
        corpus_id=corpus.id,
        numero_ciclo=numero_ciclo,
        data=datetime.now(UTC).replace(tzinfo=None),
        nota_agregada=nota_agregada,
        nota_por_campo=nota_por_campo,
        sugestao_artifact_id=artifact.id,
        shadow_run_ids=ids_ok,
    )
    db.add(ciclo)
    db.commit()
    db.refresh(ciclo)
    db.refresh(artifact)

    return {
        "fase": "sugestao_prompt_geral",
        "corpus_id": str(corpus.id),
        "corpus_slug": corpus.slug,
        "aplicacao_origem": corpus.aplicacao_origem or "Mativas",
        "versao_corpus_mistas": misturou_versoes,
        "versoes_corpus": {sid: ver for sid, ver in versoes},
        "aviso_versoes": aviso_versoes,
        "comparavel_com_confianca": not misturou_versoes,
        "ciclo": {
            "id": str(ciclo.id),
            "numero_ciclo": ciclo.numero_ciclo,
            "nota_agregada": ciclo.nota_agregada,
            "nota_por_campo": ciclo.nota_por_campo,
            "data": ciclo.data.isoformat() if ciclo.data else None,
            "shadow_run_ids": ids_ok,
            "comparavel_com_confianca": not misturou_versoes,
        },
        "sugestao": {
            "id": str(artifact.id),
            "markdown": artifact.markdown,
            "meta": artifact.meta,
        },
        "disclaimer": (
            "Sugestão somente para cópia manual. Nenhuma escrita automática "
            "em sistema externo."
        ),
    }


def list_ciclos(db: Session, corpus_id: UUID | str) -> list[dict[str, Any]]:
    corpus = get_corpus(db, corpus_id)
    ciclos = (
        db.query(CrystalCicloMelhoria)
        .filter(CrystalCicloMelhoria.corpus_id == corpus.id)
        .order_by(CrystalCicloMelhoria.numero_ciclo.desc())
        .all()
    )
    from services.crystal_ball.models import CrystalResultadoReal

    out: list[dict[str, Any]] = []
    for c in ciclos:
        reais = (
            db.query(CrystalResultadoReal)
            .filter(
                CrystalResultadoReal.corpus_id == corpus.id,
                CrystalResultadoReal.numero_ciclo == c.numero_ciclo,
            )
            .order_by(CrystalResultadoReal.created_at.desc())
            .all()
        )
        nota_real = None
        if reais:
            ratios = [
                r.comparison.get("nota_agregada")
                or r.comparison.get("identical_ratio")
                for r in reais
                if isinstance(r.comparison, dict)
            ]
            nums = [float(x) for x in ratios if isinstance(x, (int, float))]
            if nums:
                nota_real = sum(nums) / len(nums)
        art_meta: dict[str, Any] = {}
        if c.sugestao_artifact_id:
            from services.crystal_ball.models import CrystalSugestaoArtifact

            art = db.get(CrystalSugestaoArtifact, c.sugestao_artifact_id)
            if art and isinstance(art.meta, dict):
                art_meta = art.meta

        reais_resumo = []
        for r in reais[:5]:
            cmp_r = r.comparison if isinstance(r.comparison, dict) else {}
            reais_resumo.append(
                {
                    "id": str(r.id),
                    "versao_corpus": r.versao_corpus,
                    "versao_prompt_origem": r.versao_prompt_origem,
                    "comparavel_com_confianca": cmp_r.get(
                        "comparavel_com_confianca", True
                    ),
                    "avisos_integridade": cmp_r.get("avisos_integridade") or [],
                }
            )

        out.append(
            {
                "id": str(c.id),
                "numero_ciclo": c.numero_ciclo,
                "data": c.data.isoformat() if c.data else None,
                "nota_agregada_simulada": c.nota_agregada,
                "nota_agregada_real": nota_real,
                "nota_por_campo": c.nota_por_campo,
                "sugestao_artifact_id": (
                    str(c.sugestao_artifact_id) if c.sugestao_artifact_id else None
                ),
                "n_resultados_reais": len(reais),
                "shadow_run_ids": c.shadow_run_ids,
                "versao_corpus_mistas": bool(art_meta.get("versao_corpus_mistas")),
                "comparavel_com_confianca": art_meta.get(
                    "comparavel_com_confianca", True
                ),
                "resultados_reais": reais_resumo,
            }
        )
    return out
