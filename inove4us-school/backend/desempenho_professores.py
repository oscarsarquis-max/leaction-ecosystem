"""Desempenho experimental por professor — componentes separados, sem nota única.

Agregado do recorte (mesmas fontes do Radar). Ordenação alfabética, nunca por métrica.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from contribuicao_agregada import classificar_aula
from radar_home import as_mesa, aula_tem_adaptacao_pei

FEATURE_KEY = "desempenho_professores_91"


def _nome_sort(email: str | None, nome: str | None) -> str:
    raw = str(nome or "").strip() or str(email or "").strip()
    return raw.casefold()


def montar_linhas(aulas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Uma linha por professor. Sem score, sem ordenação por desempenho."""
    buckets: dict[str, dict[str, Any]] = {}
    for aula in aulas:
        pid = str(aula.get("professor_vinculo_id") or "").strip()
        if not pid:
            continue
        b = buckets.get(pid)
        if b is None:
            b = {
                "professor_vinculo_id": pid,
                "professor_email": aula.get("professor_email"),
                "professor_nome": aula.get("professor_nome"),
                "aulas_total": 0,
                "aulas_dia_a_dia": 0,
                "aulas_desafio": 0,
                "metodologias": set(),
                "adesao_canonica": 0,
                "adesao_personalizada": 0,
                "adesao_sem_carimbo": 0,
                "curadoria_enviadas": 0,
                "aulas_pei_aplicadas": 0,
                "turma_ids": set(),
            }
            buckets[pid] = b
        if aula.get("professor_nome") and not b.get("professor_nome"):
            b["professor_nome"] = aula.get("professor_nome")
        b["aulas_total"] += 1
        if aula.get("tipo_aula") == "desafio":
            b["aulas_desafio"] += 1
        else:
            b["aulas_dia_a_dia"] += 1
        met = str(aula.get("metodologia_nome") or "").strip()
        if met:
            b["metodologias"].add(met)
        kind = classificar_aula(aula.get("mesa") or {})
        if kind == "canonica":
            b["adesao_canonica"] += 1
        elif kind == "personalizada":
            b["adesao_personalizada"] += 1
        else:
            b["adesao_sem_carimbo"] += 1
        if aula.get("has_curadoria"):
            b["curadoria_enviadas"] += 1
        if aula_tem_adaptacao_pei(aula.get("mesa") or {}):
            b["aulas_pei_aplicadas"] += 1
        tid = aula.get("turma_id")
        if tid:
            b["turma_ids"].add(str(tid))

    linhas: list[dict[str, Any]] = []
    for b in buckets.values():
        mets = sorted(b["metodologias"], key=str.casefold)
        linhas.append(
            {
                "professor_vinculo_id": b["professor_vinculo_id"],
                "professor_email": b.get("professor_email"),
                "professor_nome": b.get("professor_nome"),
                "aulas_total": b["aulas_total"],
                "aulas_dia_a_dia": b["aulas_dia_a_dia"],
                "aulas_desafio": b["aulas_desafio"],
                "metodologias_distintas": len(mets),
                "metodologias": mets,
                "adesao": {
                    "canonica": b["adesao_canonica"],
                    "personalizada": b["adesao_personalizada"],
                    "sem_carimbo": b["adesao_sem_carimbo"],
                },
                "curadoria_enviadas": b["curadoria_enviadas"],
                "pei": {
                    "aulas_com_adaptacao": b["aulas_pei_aplicadas"],
                    "alunos_pei_nas_turmas": int(b.get("alunos_pei_nas_turmas") or 0),
                },
                "_turma_ids": b["turma_ids"],
            }
        )
    linhas.sort(
        key=lambda r: (
            _nome_sort(r.get("professor_email"), r.get("professor_nome")),
            r["professor_vinculo_id"],
        )
    )
    return linhas


def fetch_desempenho(
    cur: Any,
    *,
    instituicao_id: str,
    data_inicio: date,
    data_fim: date,
    unidade_id: str | None = None,
    metodologia: str | None = None,
) -> dict[str, Any]:
    sql = """
        SELECT
            p.id,
            p.professor_vinculo_id,
            v.email_convite AS professor_email,
            p.mesa_payload_json,
            p.tipo_aula,
            p.turma_id,
            m.nome AS metodologia_nome,
            EXISTS (
                SELECT 1 FROM public.school_curadoria_metodologias c
                WHERE c.plano_espelhado_id = p.id
            ) AS has_curadoria
        FROM public.school_planos_aula_espelhados p
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_unidades u ON u.id = t.unidade_id
        JOIN public.school_metodologias_catalogo m ON m.id = p.metodologia_catalogo_id
        LEFT JOIN public.school_professores_vinculo v ON v.id = p.professor_vinculo_id
        WHERE u.instituicao_id = %s
          AND u.ativo = TRUE
          AND p.semana_referencia >= %s
          AND p.semana_referencia <= %s
    """
    params: list[Any] = [str(instituicao_id), data_inicio, data_fim]
    if unidade_id:
        sql += " AND t.unidade_id = %s"
        params.append(str(unidade_id))
    if metodologia:
        sql += " AND m.nome = %s"
        params.append(metodologia)
    cur.execute(sql, params)
    aulas = []
    for r in cur.fetchall():
        mesa = as_mesa(r.get("mesa_payload_json"))
        aulas.append(
            {
                "professor_vinculo_id": str(r["professor_vinculo_id"]),
                "professor_email": r.get("professor_email"),
                "professor_nome": mesa.get("professor_nome"),
                "mesa": mesa,
                "tipo_aula": r.get("tipo_aula"),
                "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
                "metodologia_nome": r.get("metodologia_nome"),
                "has_curadoria": bool(r.get("has_curadoria")),
            }
        )

    linhas = montar_linhas(aulas)
    turma_ids = set()
    for row in linhas:
        turma_ids.update(row.get("_turma_ids") or [])

    pei_por_turma: dict[str, int] = defaultdict(int)
    if turma_ids:
        cur.execute(
            """
            SELECT a.turma_id::text AS turma_id, COUNT(DISTINCT p.id)::int AS n
            FROM public.school_pei_alunos p
            JOIN public.school_alunos a ON a.id = p.aluno_id
            WHERE p.instituicao_id = %s
              AND p.status = 'ativo'
              AND a.turma_id = ANY(%s::uuid[])
            GROUP BY a.turma_id
            """,
            (str(instituicao_id), list(turma_ids)),
        )
        for hit in cur.fetchall():
            pei_por_turma[str(hit["turma_id"])] = int(hit.get("n") or 0)

    out = []
    for row in linhas:
        n_pei = sum(pei_por_turma.get(tid, 0) for tid in (row.get("_turma_ids") or []))
        pei = dict(row["pei"])
        pei["alunos_pei_nas_turmas"] = n_pei
        clean = {k: v for k, v in row.items() if k != "_turma_ids"}
        clean["pei"] = pei
        out.append(clean)

    return {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "experimental": True,
        "feature_key": FEATURE_KEY,
        "professores": out,
    }


def ensure_feedback_table(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.school_feedback_features (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instituicao_id  UUID NOT NULL
                REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
            gestor_id       UUID,
            gestor_email    TEXT,
            gestor_nome     TEXT,
            feature_key     TEXT NOT NULL,
            texto           TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_school_feedback_features_inst_feat
            ON public.school_feedback_features
            (instituicao_id, feature_key, created_at DESC)
        """
    )


def inserir_feedback(
    cur: Any,
    *,
    instituicao_id: str,
    gestor_id: str | None,
    gestor_email: str | None,
    gestor_nome: str | None,
    texto: str,
    feature_key: str = FEATURE_KEY,
) -> dict[str, Any]:
    ensure_feedback_table(cur)
    cur.execute(
        """
        INSERT INTO public.school_feedback_features (
            instituicao_id, gestor_id, gestor_email, gestor_nome, feature_key, texto
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, created_at
        """,
        (
            str(instituicao_id),
            str(gestor_id) if gestor_id else None,
            (gestor_email or "").strip() or None,
            (gestor_nome or "").strip() or None,
            feature_key,
            texto.strip(),
        ),
    )
    row = cur.fetchone() or {}
    return {
        "id": str(row["id"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def listar_feedback(
    cur: Any,
    *,
    instituicao_id: str,
    feature_key: str = FEATURE_KEY,
    limite: int = 50,
) -> list[dict[str, Any]]:
    ensure_feedback_table(cur)
    cur.execute(
        """
        SELECT id, gestor_nome, gestor_email, texto, created_at, feature_key
        FROM public.school_feedback_features
        WHERE instituicao_id = %s AND feature_key = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (str(instituicao_id), feature_key, int(limite)),
    )
    itens = []
    for r in cur.fetchall():
        itens.append(
            {
                "id": str(r["id"]),
                "gestor_nome": r.get("gestor_nome"),
                "gestor_email": r.get("gestor_email"),
                "texto": r.get("texto"),
                "feature_key": r.get("feature_key"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
        )
    return itens
