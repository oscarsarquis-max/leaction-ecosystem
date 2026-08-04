"""Equipe — licenças + convites + status pedagógico (zona administrativo).

Etapa 12/15:
- licenças contratadas / em uso (vínculos ativos) / disponíveis
- link Action Hub
- status pedagógico a partir de school_planos_aula_espelhados (espelho B2C)
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("equipe", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_STATUS_LABEL = {
    "pendente": "Pendente",
    "ativo": "Ativo",
    "suspenso": "Suspenso",
    "revogado": "Revogado",
}


def _parse_uuid(value: str, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _email_ok(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


def _provisional_b2c_id(email: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"inove4us-school:convite:{email}")


def _status_pedagogico(stats: dict[str, Any] | None) -> dict[str, Any]:
    if not stats or int(stats.get("total") or 0) == 0:
        return {
            "codigo": "sem_planos",
            "label": "Sem planos",
            "detalhe": "Ainda sem espelho de execução no B2C",
            "pendentes": 0,
            "aprovados": 0,
            "reprovados": 0,
            "total": 0,
        }
    pend = int(stats.get("pendentes") or 0)
    apr = int(stats.get("aprovados") or 0)
    rep = int(stats.get("reprovados") or 0)
    total = int(stats.get("total") or 0)
    if pend > 0:
        return {
            "codigo": "pendencias",
            "label": f"{pend} pendente(s)",
            "detalhe": f"{total} plano(s) espelhados · {apr} aprovado(s)",
            "pendentes": pend,
            "aprovados": apr,
            "reprovados": rep,
            "total": total,
        }
    if rep > 0:
        return {
            "codigo": "reprovacoes",
            "label": f"{rep} reprovado(s)",
            "detalhe": f"{total} plano(s) · {apr} aprovado(s)",
            "pendentes": pend,
            "aprovados": apr,
            "reprovados": rep,
            "total": total,
        }
    return {
        "codigo": "em_dia",
        "label": "Em dia",
        "detalhe": f"{apr} plano(s) aprovado(s)",
        "pendentes": pend,
        "aprovados": apr,
        "reprovados": rep,
        "total": total,
    }


def _serialize_vinculo(row: dict[str, Any], ped: dict[str, Any]) -> dict:
    status = row["status_vinculo"]
    return {
        "id": str(row["id"]),
        "email": row.get("email_convite") or None,
        "professor_b2c_id": str(row["professor_b2c_id"]),
        "status": _STATUS_LABEL.get(status, status),
        "status_vinculo": status,
        "convidadoEm": row["created_at"].date().isoformat()
        if row.get("created_at")
        else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "status_pedagogico": ped,
    }


def _licencas_payload(cur: Any, instituicao_id: uuid.UUID) -> dict | tuple:
    cur.execute(
        """
        SELECT licencas_contratadas, link_plano_actionhub, razao_social
        FROM public.school_instituicoes
        WHERE id = %s
        """,
        (str(instituicao_id),),
    )
    inst = cur.fetchone()
    if not inst:
        return jsonify({"error": "Instituição não encontrada"}), 404

    # Etapa 12: usuários ativos = vínculos status ativo (+ gestores ativos)
    cur.execute(
        """
        SELECT count(*)::int AS n
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s AND status_vinculo = 'ativo'
        """,
        (str(instituicao_id),),
    )
    prof_ativos = int(cur.fetchone()["n"] or 0)
    cur.execute(
        """
        SELECT count(*)::int AS n
        FROM public.school_gestores
        WHERE instituicao_id = %s AND ativo = TRUE
        """,
        (str(instituicao_id),),
    )
    gest_ativos = int(cur.fetchone()["n"] or 0)
    em_uso = prof_ativos  # licença de professor; gestores não consomem a mesma quota

    # Fonte canônica pós-Hub: school_licencas; fallback coluna legado na instituição
    cur.execute(
        """
        SELECT total_assentos, assentos_em_uso, sku_ultimo
        FROM public.school_licencas
        WHERE instituicao_id = %s
        """,
        (str(instituicao_id),),
    )
    lic_row = cur.fetchone()
    if lic_row is not None:
        contratadas = int(lic_row["total_assentos"] or 0)
        if int(lic_row["assentos_em_uso"] or 0) != em_uso:
            cur.execute(
                """
                UPDATE public.school_licencas
                SET assentos_em_uso = %s, updated_at = CURRENT_TIMESTAMP
                WHERE instituicao_id = %s
                """,
                (em_uso, str(instituicao_id)),
            )
    else:
        contratadas = inst["licencas_contratadas"]

    disponiveis = None if contratadas is None else max(0, int(contratadas) - em_uso)

    return {
        "razao_social": inst["razao_social"],
        "licencas_contratadas": contratadas,
        "licencas_em_uso": em_uso,
        "licencas_disponiveis": disponiveis,
        "professores_ativos": prof_ativos,
        "gestores_ativos": gest_ativos,
        "link_plano_actionhub": inst["link_plano_actionhub"],
        "sku_ultimo": (lic_row or {}).get("sku_ultimo") if lic_row else None,
        "no_limite": contratadas is not None and em_uso >= int(contratadas),
    }


def _pedagogico_map(cur: Any, instituicao_id: uuid.UUID) -> dict[str, dict]:
    cur.execute(
        """
        SELECT
            p.professor_vinculo_id::text AS vid,
            count(*)::int AS total,
            count(*) FILTER (WHERE p.status = 'pendente')::int AS pendentes,
            count(*) FILTER (WHERE p.status = 'aprovado')::int AS aprovados,
            count(*) FILTER (WHERE p.status = 'reprovado')::int AS reprovados
        FROM public.school_planos_aula_espelhados p
        WHERE p.instituicao_id = %s
        GROUP BY p.professor_vinculo_id
        """,
        (str(instituicao_id),),
    )
    return {r["vid"]: r for r in cur.fetchall()}


@bp.get("/api/instituicoes/<instituicao_id>/equipe")
def get_equipe(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if isinstance(parsed, tuple):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            lic = _licencas_payload(cur, parsed)
            if isinstance(lic, tuple):
                return lic
            ped_map = _pedagogico_map(cur, parsed)

            cur.execute(
                """
                SELECT id, professor_b2c_id, email_convite, status_vinculo, created_at
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s
                  AND status_vinculo <> 'revogado'
                ORDER BY
                  CASE status_vinculo
                    WHEN 'pendente' THEN 0
                    WHEN 'ativo' THEN 1
                    ELSE 2
                  END,
                  created_at DESC
                """,
                (str(parsed),),
            )
            membros = []
            for r in cur.fetchall():
                ped = _status_pedagogico(ped_map.get(str(r["id"])))
                membros.append(_serialize_vinculo(r, ped))

    return jsonify({"licencas": lic, "membros": membros})


@bp.post("/api/instituicoes/<instituicao_id>/equipe/convites")
def convidar(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if isinstance(parsed, tuple):
        return parsed

    body = request.get_json(silent=True) or {}
    email = str(body.get("email") or "").strip().lower()
    if not _email_ok(email):
        return jsonify({"error": "Informe um e-mail válido."}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            lic = _licencas_payload(cur, parsed)
            if isinstance(lic, tuple):
                return lic
            if lic.get("no_limite"):
                return (
                    jsonify(
                        {
                            "error": (
                                "Limite de licenças atingido. "
                                "Revogue um vínculo ou atualize o plano no Action Hub."
                            ),
                            "licencas": lic,
                        }
                    ),
                    402,
                )

            cur.execute(
                """
                SELECT id, status_vinculo
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s
                  AND (
                    lower(email_convite) = %s
                    OR professor_b2c_id = %s
                  )
                LIMIT 1
                """,
                (str(parsed), email, str(_provisional_b2c_id(email))),
            )
            existing = cur.fetchone()
            if existing and existing["status_vinculo"] != "revogado":
                return jsonify({"error": "Este professor já está na lista."}), 409

            b2c_id = _provisional_b2c_id(email)
            if existing and existing["status_vinculo"] == "revogado":
                cur.execute(
                    """
                    UPDATE public.school_professores_vinculo
                    SET email_convite = %s,
                        status_vinculo = 'pendente',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, professor_b2c_id, email_convite, status_vinculo, created_at
                    """,
                    (email, str(existing["id"])),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO public.school_professores_vinculo
                        (instituicao_id, professor_b2c_id, email_convite, status_vinculo)
                    VALUES (%s, %s, %s, 'pendente')
                    RETURNING id, professor_b2c_id, email_convite, status_vinculo, created_at
                    """,
                    (str(parsed), str(b2c_id), email),
                )
            row = cur.fetchone()
            lic = _licencas_payload(cur, parsed)
            if isinstance(lic, tuple):
                return lic
            ped = _status_pedagogico(None)

    return jsonify({"membro": _serialize_vinculo(row, ped), "licencas": lic}), 201


@bp.post("/api/instituicoes/<instituicao_id>/equipe/<vinculo_id>/revogar")
def revogar(instituicao_id: str, vinculo_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    vid = _parse_uuid(vinculo_id, "vínculo")
    if isinstance(vid, tuple):
        return vid

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_professores_vinculo
                SET status_vinculo = 'revogado',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                  AND status_vinculo <> 'revogado'
                RETURNING id, email_convite
                """,
                (str(vid), str(inst)),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Vínculo não encontrado"}), 404
            lic = _licencas_payload(cur, inst)
            if isinstance(lic, tuple):
                return lic

    return jsonify(
        {
            "ok": True,
            "revogado": str(row["id"]),
            "email": row.get("email_convite"),
            "licencas": lic,
        }
    )


@bp.get("/api/instituicoes/<instituicao_id>/equipe/<vinculo_id>/radiografia")
def radiografia(instituicao_id: str, vinculo_id: str):
    """Radiografia do professor: recursos, entrega, metodologias, disciplinas,
    avaliações declaradas e registros de execução alinhados à metodologia da escola.
    """
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    vid = _parse_uuid(vinculo_id, "vínculo")
    if isinstance(vid, tuple):
        return vid

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, professor_b2c_id, email_convite, status_vinculo, created_at
                FROM public.school_professores_vinculo
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(vid), str(inst)),
            )
            vinculo = cur.fetchone()
            if not vinculo:
                return jsonify({"error": "Vínculo não encontrado"}), 404

            # Recursos explícitos + licença implícita se ativo
            cur.execute(
                """
                SELECT id, titulo, tipo, detalhe, concedido_em, ativo
                FROM public.school_professor_recursos
                WHERE professor_vinculo_id = %s AND ativo = TRUE
                ORDER BY concedido_em DESC, created_at DESC
                """,
                (str(vid),),
            )
            recursos = [
                {
                    "id": str(r["id"]),
                    "titulo": r["titulo"],
                    "tipo": r["tipo"],
                    "detalhe": r.get("detalhe"),
                    "concedido_em": r["concedido_em"].isoformat()
                    if r.get("concedido_em")
                    else None,
                }
                for r in cur.fetchall()
            ]
            if vinculo["status_vinculo"] == "ativo" and not any(
                x["tipo"] == "licenca" for x in recursos
            ):
                recursos.insert(
                    0,
                    {
                        "id": None,
                        "titulo": "Licença institucional",
                        "tipo": "licenca",
                        "detalhe": "Assento ativo no plano da escola",
                        "concedido_em": vinculo["created_at"].date().isoformat()
                        if vinculo.get("created_at")
                        else None,
                    },
                )

            # Metodologias ativas da escola (repertório liberado)
            cur.execute(
                """
                SELECT c.nome
                FROM public.school_metodologia_config cfg
                JOIN public.school_metodologias_catalogo c
                  ON c.id = cfg.metodologia_catalogo_id
                WHERE cfg.instituicao_id = %s
                  AND cfg.is_active = TRUE
                  AND c.ativo = TRUE
                ORDER BY c.nome
                LIMIT 40
                """,
                (str(inst),),
            )
            metodologias_liberadas = [r["nome"] for r in cur.fetchall()]

            # Disciplinas sob comando
            cur.execute(
                """
                SELECT pt.disciplina, t.nome AS turma_nome, pt.ativo
                FROM public.school_professor_turma pt
                JOIN public.school_turmas t ON t.id = pt.turma_id
                WHERE pt.professor_vinculo_id = %s
                ORDER BY pt.ativo DESC, pt.disciplina, t.nome
                """,
                (str(vid),),
            )
            disciplinas = [
                {
                    "disciplina": r["disciplina"],
                    "turma": r["turma_nome"],
                    "ativo": bool(r["ativo"]),
                }
                for r in cur.fetchall()
            ]

            # Entrega + metodologias usadas + execuções (planos espelhados)
            cur.execute(
                """
                SELECT
                    p.id,
                    p.semana_referencia,
                    p.tipo_aula,
                    p.status,
                    p.conteudo_resumo,
                    p.observacoes_coordenador,
                    p.desafio_titulo,
                    p.desafio_sequencia,
                    m.nome AS metodologia_nome,
                    t.nome AS turma_nome
                FROM public.school_planos_aula_espelhados p
                JOIN public.school_metodologias_catalogo m
                  ON m.id = p.metodologia_catalogo_id
                JOIN public.school_turmas t ON t.id = p.turma_id
                WHERE p.professor_vinculo_id = %s AND p.instituicao_id = %s
                ORDER BY p.semana_referencia DESC, p.created_at DESC
                LIMIT 50
                """,
                (str(vid), str(inst)),
            )
            planos = cur.fetchall()
            metodologias_usadas = sorted(
                {r["metodologia_nome"] for r in planos if r.get("metodologia_nome")}
            )
            entrega = {
                "planos_total": len(planos),
                "aprovados": sum(1 for r in planos if r["status"] == "aprovado"),
                "pendentes": sum(1 for r in planos if r["status"] == "pendente"),
                "reprovados": sum(1 for r in planos if r["status"] == "reprovado"),
                "dia_a_dia": sum(1 for r in planos if r["tipo_aula"] == "dia_a_dia"),
                "desafio": sum(1 for r in planos if r["tipo_aula"] == "desafio"),
                "metodologias_distintas": len(metodologias_usadas),
                "disciplinas_ativas": sum(1 for d in disciplinas if d["ativo"]),
            }
            execucoes = [
                {
                    "id": str(r["id"]),
                    "semana_referencia": r["semana_referencia"].isoformat(),
                    "tipo_aula": r["tipo_aula"],
                    "status": r["status"],
                    "metodologia": r["metodologia_nome"],
                    "turma": r["turma_nome"],
                    "resumo": r.get("conteudo_resumo"),
                    "desafio_titulo": r.get("desafio_titulo"),
                    "desafio_sequencia": r.get("desafio_sequencia"),
                    "observacoes_coordenador": r.get("observacoes_coordenador"),
                    "alinhado_metodologia_escola": True,
                }
                for r in planos
            ]

            # Avaliações declaradas
            cur.execute(
                """
                SELECT id, nota, referencia, observacao, declarado_em
                FROM public.school_professor_avaliacoes
                WHERE professor_vinculo_id = %s
                ORDER BY declarado_em DESC, created_at DESC
                """,
                (str(vid),),
            )
            avaliacoes = [
                {
                    "id": str(r["id"]),
                    "nota": float(r["nota"]),
                    "referencia": r["referencia"],
                    "observacao": r.get("observacao"),
                    "declarado_em": r["declarado_em"].isoformat()
                    if r.get("declarado_em")
                    else None,
                }
                for r in cur.fetchall()
            ]
            nota_atual = avaliacoes[0] if avaliacoes else None

    return jsonify(
        {
            "professor": {
                "id": str(vinculo["id"]),
                "email": vinculo.get("email_convite"),
                "status_vinculo": vinculo["status_vinculo"],
                "professor_b2c_id": str(vinculo["professor_b2c_id"]),
            },
            "recursos_recebidos": recursos,
            "metodologias_liberadas_escola": metodologias_liberadas,
            "entrega": entrega,
            "metodologias_usadas": metodologias_usadas,
            "disciplinas": disciplinas,
            "avaliacao": {
                "atual": nota_atual,
                "historico": avaliacoes,
            },
            "execucoes": execucoes,
        }
    )


@bp.post("/api/instituicoes/<instituicao_id>/equipe/<vinculo_id>/avaliacoes")
def declarar_avaliacao(instituicao_id: str, vinculo_id: str):
    """Declara / atualiza nota de desempenho (histórico por referência)."""
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    vid = _parse_uuid(vinculo_id, "vínculo")
    if isinstance(vid, tuple):
        return vid
    body = request.get_json(silent=True) or {}
    referencia = str(body.get("referencia") or "").strip()
    if not referencia:
        return jsonify({"error": "Informe a referência do ciclo"}), 400
    try:
        nota = float(body.get("nota"))
    except (TypeError, ValueError):
        return jsonify({"error": "Nota inválida"}), 400
    if nota < 0 or nota > 10:
        return jsonify({"error": "Nota deve estar entre 0 e 10"}), 400
    try:
        gestor = uuid.UUID(str(body["gestor_id"])) if body.get("gestor_id") else None
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "Identificador de gestor inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_professores_vinculo
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(vid), str(inst)),
            )
            if not cur.fetchone():
                return jsonify({"error": "Vínculo não encontrado"}), 404
            cur.execute(
                """
                INSERT INTO public.school_professor_avaliacoes (
                    professor_vinculo_id, nota, referencia, observacao,
                    declarado_por_gestor_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (professor_vinculo_id, referencia) DO UPDATE SET
                    nota = EXCLUDED.nota,
                    observacao = EXCLUDED.observacao,
                    declarado_por_gestor_id = EXCLUDED.declarado_por_gestor_id,
                    declarado_em = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, nota, referencia, observacao, declarado_em
                """,
                (
                    str(vid),
                    nota,
                    referencia,
                    str(body.get("observacao") or "").strip() or None,
                    str(gestor) if gestor else None,
                ),
            )
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "nota": float(r["nota"]),
                    "referencia": r["referencia"],
                    "observacao": r.get("observacao"),
                    "declarado_em": r["declarado_em"].isoformat(),
                }
            }
        ),
        201,
    )
