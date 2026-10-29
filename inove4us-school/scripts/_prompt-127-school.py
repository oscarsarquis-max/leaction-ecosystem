#!/usr/bin/env python3
"""127 — Secretaria + PEI + comunicados reais (Escola Teste). Não limpa."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
OPER = "operacional@escolateste.edu.br"
ADMIN = "admin@escolateste.edu.br"
TZ = ZoneInfo("America/Sao_Paulo")
OUT = Path("/tmp/prompt-127-school.json")

ALUNOS = {
    "6A": [
        ("Lucas Mendes", "ET-2026-101"),
        ("Beatriz Oliveira", "ET-2026-102"),
        ("Gabriel Souza", "ET-2026-103"),
        ("Larissa Costa", "ET-2026-104"),
        ("Matheus Lima", "ET-2026-105"),
        ("Isabela Rocha", "ET-2026-106"),
    ],
    "1A": [
        ("Mariana Duarte", "ET-2026-004"),
        ("Felipe Andrade", "ET-2026-005"),
        ("Camila Borges", "ET-2026-006"),
        ("Rafael Cunha", "ET-2026-007"),
        ("Letícia Prado", "ET-2026-008"),
        ("Vinícius Lopes", "ET-2026-009"),
    ],
    "9A": [
        ("Caio Moreira", "ET-2026-201"),
        ("Sofia Carvalho", "ET-2026-202"),
        ("Enzo Araujo", "ET-2026-203"),
        ("Valentina Dias", "ET-2026-204"),
        ("Davi Nascimento", "ET-2026-205"),
        ("Helena Castro", "ET-2026-206"),
    ],
}

PEIS = [
    ("Lucas Mendes", "TEA", "6A"),
    ("Mariana Duarte", "TDAH", "1A"),
    ("Caio Moreira", "Deficiência Visual", "9A"),
]


def gestor(email: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                       i.razao_social AS instituicao_nome,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                  FROM public.school_gestores g
                  JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                  LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                 WHERE g.instituicao_id = %s AND lower(g.email) = %s
                 GROUP BY g.id, i.razao_social
                """,
                (INST, email),
            )
            row = cur.fetchone()
    if not row:
        raise SystemExit(f"gestor ausente: {email}")
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "instituicao_nome": row.get("instituicao_nome"),
        "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
        "nome": row["nome"],
        "email": row["email"],
        "cargo": row["cargo"],
        "zonas": list(row["zonas"] or []),
    }


def client_for(email: str):
    from app import app

    user = gestor(email)
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c, user


def slim(r):
    return {"http": r.status_code, "body": r.get_json(silent=True) or {}}


def catalog():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT u.id::text AS unidade_id, u.nome
                  FROM public.school_unidades u
                 WHERE u.instituicao_id = %s AND u.ativo IS NOT FALSE
                 ORDER BY u.nome LIMIT 1
                """,
                (INST,),
            )
            unidade = dict(cur.fetchone())
            cur.execute(
                """
                SELECT id::text AS periodo_id, rotulo
                  FROM public.school_periodos_letivos
                 WHERE instituicao_id = %s AND ativo IS NOT FALSE
                 ORDER BY ano_letivo DESC LIMIT 1
                """,
                (INST,),
            )
            periodo = dict(cur.fetchone())
            cur.execute(
                """
                SELECT c.id::text AS curso_id, c.nome, c.nivel,
                       d.id::text AS disciplina_id, d.nome AS disciplina
                  FROM public.school_curso_disciplinas cd
                  JOIN public.school_cursos c ON c.id = cd.curso_id
                  JOIN public.school_disciplinas d ON d.id = cd.disciplina_id
                  JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                 WHERE p.instituicao_id = %s
                 ORDER BY c.nome, d.nome
                """,
                (INST,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT t.id::text, t.nome, t.curso_id::text, c.nome AS curso
                  FROM public.school_turmas t
                  LEFT JOIN public.school_cursos c ON c.id = t.curso_id
                 WHERE t.instituicao_id = %s
                """,
                (INST,),
            )
            turmas = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT v.id::text, v.email_convite, v.status_vinculo
                  FROM public.school_professores_vinculo v
                 WHERE v.instituicao_id = %s
                """,
                (INST,),
            )
            vins = [dict(r) for r in cur.fetchall()]
    return {"unidade": unidade, "periodo": periodo, "catalogo": rows, "turmas": turmas, "vinculos": vins}


def pick_curso(rows, *needles):
    for n in needles:
        for r in rows:
            if n.lower() in (r.get("nome") or "").lower():
                return r
    return rows[0] if rows else {}


def disc_of(rows, curso_id, *needles):
    cand = [r for r in rows if r["curso_id"] == curso_id]
    for n in needles:
        for r in cand:
            if n.lower() in (r.get("disciplina") or "").lower():
                return r
    return cand[0] if cand else {}


def ensure_turma(c, *, nome, serie, turno, unidade, periodo, curso_id):
    listed = c.get("/api/secretaria/turmas").get_json(silent=True) or {}
    hit = next((t for t in (listed.get("items") or []) if t.get("nome") == nome), None)
    if hit:
        return hit, {"http": 200, "existing": True}
    r = c.post(
        "/api/secretaria/turmas",
        json={
            "nome": nome,
            "serie_ano": serie,
            "turno": turno,
            "unidade_id": unidade,
            "periodo_letivo_id": periodo,
            "curso_id": curso_id,
        },
    )
    body = r.get_json(silent=True) or {}
    return body.get("item") or {}, slim(r)


def main() -> int:
    cat = catalog()
    rows = cat["catalogo"]
    fund = pick_curso(rows, "Fundamental II", "Fundamental")
    medio = pick_curso(rows, "Médio", "Medio", "1ª", "1a")
    if medio.get("curso_id") == fund.get("curso_id"):
        outros = [r for r in rows if r["curso_id"] != fund.get("curso_id")]
        medio = pick_curso(outros, "Médio", "Medio") if outros else fund
    fund9 = pick_curso(rows, "9", "Anos Finais")
    if fund9.get("curso_id") in {fund.get("curso_id"), medio.get("curso_id")}:
        leftover = [
            r
            for r in rows
            if r["curso_id"] not in {fund.get("curso_id"), medio.get("curso_id")}
        ]
        fund9 = leftover[0] if leftover else fund

    d_mat_6 = disc_of(rows, fund["curso_id"], "Matem")
    d_port_6 = disc_of(rows, fund["curso_id"], "Portug", "Língua")
    d_mat_em = disc_of(rows, medio["curso_id"], "Matem")
    d_hist_em = disc_of(rows, medio["curso_id"], "Histór", "Hist")
    d_mat_9 = disc_of(rows, fund9["curso_id"], "Matem", "Ciênc")

    out = {
        "prompt": 127,
        "cursos": {
            "fund": fund,
            "medio": medio,
            "terceiro": fund9,
            "d_mat_6": d_mat_6,
            "d_port_6": d_port_6,
            "d_mat_em": d_mat_em,
            "d_hist_em": d_hist_em,
            "d_mat_9": d_mat_9,
        },
    }

    c_op, _ = client_for(OPER)
    unidade = cat["unidade"]["unidade_id"]
    periodo = cat["periodo"]["periodo_id"]

    t6, r6 = ensure_turma(
        c_op,
        nome="6º Ano A",
        serie=fund.get("nivel") or "fundamental",
        turno="manha",
        unidade=unidade,
        periodo=periodo,
        curso_id=fund["curso_id"],
    )
    t1, r1 = ensure_turma(
        c_op,
        nome="1ª Série A",
        serie=medio.get("nivel") or "medio",
        turno="manha",
        unidade=unidade,
        periodo=periodo,
        curso_id=medio["curso_id"],
    )
    t9, r9 = ensure_turma(
        c_op,
        nome="9º Ano A",
        serie=fund9.get("nivel") or "fundamental",
        turno="tarde",
        unidade=unidade,
        periodo=periodo,
        curso_id=fund9["curso_id"],
    )
    turmas = {"6A": t6, "1A": t1, "9A": t9}
    out["turmas"] = {"6A": {"id": t6.get("id"), "meta": r6}, "1A": {"id" : t1.get("id"), "meta": r1}, "9A": {"id": t9.get("id"), "meta": r9}}

    alunos_out = []
    for key, pares in ALUNOS.items():
        tid = (turmas[key] or {}).get("id")
        for nome, mat in pares:
            r = c_op.post(
                "/api/secretaria/alunos",
                json={"nome": nome, "matricula": mat, "turma_id": tid},
            )
            item = (r.get_json(silent=True) or {}).get("item") or {}
            alunos_out.append({"http": r.status_code, "nome": nome, "id": item.get("id"), "turma": key})
    out["alunos"] = {"n_ok": sum(1 for a in alunos_out if a["http"] in (200, 201, 409)), "items": alunos_out}

    c_ad, _ = client_for(ADMIN)
    listed = c_ad.get(f"/api/instituicoes/{INST}/equipe").get_json(silent=True) or {}
    membros = listed.get("membros") or []
    vin_h = next((m for m in membros if (m.get("email") or "").lower() == HOMOLOG), None)
    if not vin_h:
        inv = c_ad.post(f"/api/instituicoes/{INST}/equipe/convites", json={"email": HOMOLOG})
        vin_h = (inv.get_json(silent=True) or {}).get("membro")
    vin_h_id = (vin_h or {}).get("id")
    inv2 = c_ad.post(
        f"/api/instituicoes/{INST}/equipe/convites",
        json={"email": "marina.alves@escolateste.edu.br"},
    )
    marina = (inv2.get_json(silent=True) or {}).get("membro") or {}
    if inv2.status_code == 409:
        marina = next(
            (m for m in membros if "marina.alves" in (m.get("email") or "")),
            {},
        )
    if marina.get("id"):
        c_ad.post(f"/api/instituicoes/{INST}/equipe/{marina['id']}/disparar-convite")
    out["vinculos"] = {"homologador": vin_h_id, "marina": marina.get("id"), "marina_http": inv2.status_code}

    alocs = []
    specs = [
        (t6.get("id"), d_mat_6.get("disciplina_id"), vin_h_id),
        (t1.get("id"), d_mat_em.get("disciplina_id"), vin_h_id),
        (t9.get("id"), d_mat_9.get("disciplina_id"), vin_h_id),
        (t1.get("id"), (d_hist_em or d_mat_em).get("disciplina_id"), marina.get("id")),
    ]
    seen = set()
    for tid, did, pid in specs:
        if not (tid and did and pid):
            alocs.append({"skip": True, "tid": tid, "did": did, "pid": pid})
            continue
        key = (tid, did, pid)
        if key in seen:
            continue
        seen.add(key)
        r = c_op.post(
            "/api/secretaria/alocacoes",
            json={
                "unidade_id": unidade,
                "periodo_id": periodo,
                "disciplina_id": did,
                "professor_id": pid,
                "turma_id": tid,
            },
        )
        alocs.append(slim(r))
    out["alocacoes"] = alocs

    # map aluno names
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id::text, nome FROM public.school_alunos WHERE instituicao_id=%s",
                (INST,),
            )
            by_nome = {r["nome"]: r["id"] for r in cur.fetchall()}

    c_pe, _ = client_for(HOMOLOG)
    peis = []
    for nome, cond, _turma in PEIS:
        aid = by_nome.get(nome)
        r = c_pe.post(
            "/api/pei/alunos",
            json={
                "aluno_id": aid,
                "condicao_categoria": cond,
                "periodo_letivo_id": periodo,
                "nome_responsavel": "Família " + nome.split()[-1],
                "perfil_atual_habilidades": (
                    f"{nome} acompanha a turma com mediação pontual. "
                    f"A versão ativa da condição {cond} da Escola Teste orienta este PEI."
                ),
                "barreiras_identificadas": "Barreiras de participação em tarefas longas e em avaliações padronizadas.",
                "metas_desenvolvimento": "Participar das aulas com autonomia crescente e evidência visível de aprendizagem.",
                "recursos_assistivos": "Tempo extra, material visual e combinados de sala combinados com a coordenação.",
                "criterios_avaliacao_flexibilizados": "Produto alternativo + rubrica combinada com o estudante.",
                "experiencias_adaptadas_individuais": "Dupla de apoio e recorte da tarefa em etapas curtas.",
                "intervencoes_previstas": [
                    {"descricao": "Check-in semanal com o professor de Matemática", "frequencia": "semanal"}
                ],
            },
        )
        body = r.get_json(silent=True) or {}
        pid = body.get("id")
        ac = {}
        ap = {}
        if pid:
            ac = slim(c_pe.post(f"/api/pei/alunos/{pid}/assinar/coordenador", json={}))
            ap = slim(c_pe.post(f"/api/pei/alunos/{pid}/assinar/psicopedagogo", json={}))
        peis.append(
            {
                "aluno": nome,
                "condicao": cond,
                "http": r.status_code,
                "id": pid,
                "status": body.get("status"),
                "aee_versao": body.get("aee_versao"),
                "coord": ac,
                "psico": ap,
                "final": (ap.get("body") or body).get("status"),
            }
        )
    out["peis"] = peis

    now = datetime.now(TZ).replace(microsecond=0)
    inicio = now.replace(hour=8, minute=0, second=0)
    fim = inicio + timedelta(days=10)
    def iso(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    coms = []
    payloads = [
        {
            "titulo": "Reunião pedagógica — planejamento do bimestre",
            "descricao": (
                "Reunião da equipe docente no Campus Escola Teste para alinhar "
                "planejamento, AEE e evidências de aprendizagem do bimestre. "
                "Presença da coordenação pedagógica e da secretaria."
            ),
            "tipo": "reuniao_pedagogica",
            "publico_alvo": "toda_instituicao",
            "status": "publicado",
            "data_hora_inicio": iso(inicio),
            "data_hora_fim": iso(inicio + timedelta(hours=2)),
        },
        {
            "titulo": "Semana de avaliações — 6º Ano A",
            "descricao": (
                "Avaliações de Matemática e Língua Portuguesa nesta turma. "
                "Entregar planejamentos até quarta-feira e combinados de AEE com a coordenação."
            ),
            "tipo": "evento_escolar",
            "publico_alvo": "turma",
            "turma_id": t6.get("id"),
            "status": "publicado",
            "data_hora_inicio": iso(inicio + timedelta(days=1)),
            "data_hora_fim": iso(inicio + timedelta(days=5)),
        },
        {
            "titulo": "Plantão de inclusão (AEE) — Matemática",
            "descricao": (
                "Plantão de inclusão às terças, 10h–12h, para encaminhamentos de "
                "adaptação nas aulas de Matemática. Coordenação AEE atende no Campus."
            ),
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "disciplina_id": d_mat_6.get("disciplina_id") or d_mat_em.get("disciplina_id"),
            "status": "publicado",
            "data_hora_inicio": iso(inicio),
            "data_hora_fim": iso(fim),
        },
    ]
    for p in payloads:
        r = c_op.post("/api/secretaria/comunicacoes", json=p)
        item = (r.get_json(silent=True) or {}).get("item") or {}
        coms.append(
            {
                "http": r.status_code,
                "id": item.get("id"),
                "titulo": p["titulo"],
                "publico": p["publico_alvo"],
                "replicado_b2c": item.get("replicado_b2c"),
                "dispatch": (r.get_json(silent=True) or {}).get("b2c_dispatch"),
            }
        )
    out["comunicados"] = coms
    OUT.write_text(json.dumps(out, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
