#!/usr/bin/env python3
"""Seed produção — Escola Teste (escolateste.edu.br).

Idempotente por domínio/e-mail/order_id. Senhas de gestores só em stdout
(bloco CREDENTIALS); não grava em arquivo.

Fluxos reais reutilizados:
  - apply_licenses_granted (LICENSES_GRANTED / school-starter-50)
  - vínculo + TEACHER_INVITE (Minha Equipe)
  - alocação + TEACHER_ALLOCATED (Secretaria → pending B2C até aceite)

Uso (no host School, com .env de produção):
  cd /var/www/inove4us-school
  PYTHONPATH=backend backend/.venv/bin/python scripts/seed-escola-teste-producao.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from b2c_integration_service import (  # noqa: E402
    dispatch_event_to_b2c,
    dispatch_teacher_allocated,
)
from db import get_conn  # noqa: E402
from provision_selfserve import (  # noqa: E402
    apply_licenses_granted,
    generate_temp_password,
)

# --- constantes do seed (convenção de limpeza) ---
RAZAO = "Escola Teste"
DOMINIO = "escolateste.edu.br"
UNIDADE_NOME = "Campus Escola Teste"
ORDER_ID = "seed-escolateste-escola-inicial-v1"
SKU = "school-starter-50"
LICENCAS = 50
ANO = date.today().year

# cargo: CHECK school_gestores — Diretor|Coordenador|Secretaria|Neuropedagoga|Outro
GESTORES = (
    {
        "email": f"admin@{DOMINIO}",
        "nome": "Gestor Teste Administrativo",
        "zona": "administrativo",
        "cargo": "Diretor",
        "papel_equipe": "gestor_principal",
        "area": None,
    },
    {
        "email": f"pedagogico@{DOMINIO}",
        "nome": "Gestor Teste Pedagógico",
        "zona": "pedagogico",
        "cargo": "Coordenador",
        "papel_equipe": "gestor_academico",
        "area": None,
    },
    {
        "email": f"operacional@{DOMINIO}",
        "nome": "Gestor Teste Operacional",
        "zona": "operacional",
        "cargo": "Secretaria",
        "papel_equipe": "coordenador",
        "area": "Operacional",
    },
)

PROFESSORES = (
    f"professor1@{DOMINIO}",
    f"professor2@{DOMINIO}",
)


def _provisional_b2c_id(email: str) -> int:
    digest = hashlib.sha256(
        f"inove4us-school:convite:{email.strip().lower()}".encode("utf-8")
    ).digest()
    n = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
    return -(n or 1)


def _invite_url(email: str) -> str:
    frontend = (
        os.getenv("INOVE4US_B2C_FRONTEND_URL")
        or os.getenv("INOVE4US_FRONTEND_URL")
        or "https://inove4us.com.br"
    ).rstrip("/")
    return f"{frontend}/acesso?email={email}&school_invite=1"


def find_instituicao(cur) -> dict | None:
    cur.execute(
        """
        SELECT id, razao_social, dominio_email, status
        FROM public.school_instituicoes
        WHERE lower(dominio_email) = %s
           OR lower(razao_social) = lower(%s)
        ORDER BY created_at NULLS LAST
        LIMIT 1
        """,
        (DOMINIO.lower(), RAZAO),
    )
    return cur.fetchone()


def ensure_instituicao_e_plano() -> tuple[str, dict]:
    """Provisiona via caminho real LICENSES_GRANTED (sem payer_email → sem e-mail SES)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            existing = find_instituicao(cur)
            if existing:
                inst_id = str(existing["id"])
            else:
                inst_id = str(uuid.uuid4())

    # Sem payer_email: cria instituição + licenças, NÃO dispara SCHOOL_GESTOR_CREDENTIALS
    result = apply_licenses_granted(
        {
            "instituicao_id": inst_id,
            "subject_id": inst_id,
            "order_id": ORDER_ID,
            "sku": SKU,
            "licenses_granted": LICENCAS,
            "qty": LICENCAS,
            "razao_social": RAZAO,
            # sem payer_email / email de propósito
        },
        event_label="SEED_ESCOLA_TESTE",
    )

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Re-resolve se order_id idempotente apontou outra instituição
            if result.get("instituicao_id"):
                inst_id = str(result["instituicao_id"])
            cur.execute(
                """
                UPDATE public.school_instituicoes
                SET razao_social = %s,
                    dominio_email = %s,
                    status = 'ativa',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (RAZAO, DOMINIO, inst_id),
            )
            cur.execute(
                """
                SELECT id, razao_social, dominio_email, status, licencas_contratadas
                FROM public.school_instituicoes WHERE id = %s
                """,
                (inst_id,),
            )
            inst = cur.fetchone()
            cur.execute(
                """
                SELECT total_assentos, assentos_em_uso, sku_ultimo
                FROM public.school_licencas WHERE instituicao_id = %s
                """,
                (inst_id,),
            )
            lic = cur.fetchone()

    meta = {
        "provision": {
            k: result.get(k)
            for k in (
                "handled",
                "idempotent",
                "created",
                "event",
                "order_id",
                "http_status",
                "error",
                "reason",
            )
            if k in result or result.get(k) is not None
        },
        "licencas": dict(lic) if lic else None,
    }
    return inst_id, {"instituicao": dict(inst), **meta}


def upsert_gestor(cur, *, instituicao_id: str, spec: dict) -> tuple[str, str | None]:
    """Retorna (gestor_id, senha_plana_se_nova). Uma zona RBAC por gestor."""
    email = spec["email"].lower()
    cur.execute(
        "SELECT id, instituicao_id FROM public.school_gestores WHERE lower(email) = %s",
        (email,),
    )
    row = cur.fetchone()
    password: str | None = None
    if row:
        if str(row["instituicao_id"]) != instituicao_id:
            raise RuntimeError(f"e-mail {email} já pertence a outra instituição")
        gestor_id = str(row["id"])
        cur.execute(
            """
            UPDATE public.school_gestores
            SET nome = %s, cargo = %s, ativo = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (spec["nome"], spec["cargo"], gestor_id),
        )
    else:
        password = generate_temp_password()
        cur.execute(
            """
            INSERT INTO public.school_gestores (
                instituicao_id, nome, email, senha_hash, cargo, ativo
            ) VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (
                instituicao_id,
                spec["nome"],
                email,
                generate_password_hash(password),
                spec["cargo"],
            ),
        )
        gestor_id = str(cur.fetchone()["id"])

    # Só a zona pedida ativa; desativa outras do mesmo gestor nesta instituição
    for zona in ("administrativo", "pedagogico", "operacional"):
        ativo = zona == spec["zona"]
        cur.execute(
            """
            INSERT INTO public.school_gestor_perfis (gestor_id, zona, ativo)
            VALUES (%s, %s, %s)
            ON CONFLICT (gestor_id, zona) DO UPDATE SET
                ativo = EXCLUDED.ativo,
                updated_at = CURRENT_TIMESTAMP
            """,
            (gestor_id, zona, ativo),
        )
    return gestor_id, password


def ensure_unidade(cur, instituicao_id: str) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_unidades
        WHERE instituicao_id = %s AND lower(nome) = lower(%s)
        LIMIT 1
        """,
        (instituicao_id, UNIDADE_NOME),
    )
    row = cur.fetchone()
    endereco = "Rua das Acácias, 100 — Jardim Teste"
    if row:
        uid = str(row["id"])
        cur.execute(
            """
            UPDATE public.school_unidades SET
                endereco = %s,
                logradouro = %s,
                numero = %s,
                bairro = %s,
                cep = %s,
                cidade = %s,
                uf = %s,
                telefone = %s,
                email_institucional = %s,
                ativo = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                endereco,
                "Rua das Acácias",
                "100",
                "Jardim Teste",
                "01310-100",
                "São Paulo",
                "SP",
                "(11) 3000-0000",
                f"contato@{DOMINIO}",
                uid,
            ),
        )
        return uid

    cur.execute(
        """
        INSERT INTO public.school_unidades (
            instituicao_id, nome, endereco, codigo, cidade, uf,
            logradouro, numero, bairro, cep, telefone, email_institucional
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            instituicao_id,
            UNIDADE_NOME,
            endereco,
            "ET-01",
            "São Paulo",
            "SP",
            "Rua das Acácias",
            "100",
            "Jardim Teste",
            "01310-100",
            "(11) 3000-0000",
            f"contato@{DOMINIO}",
        ),
    )
    return str(cur.fetchone()["id"])


def ensure_equipe(cur, unidade_id: str, gestores: dict[str, str]) -> None:
    for spec in GESTORES:
        gid = gestores[spec["email"]]
        cur.execute(
            """
            SELECT id FROM public.school_unidade_equipe
            WHERE unidade_id = %s AND papel = %s AND ativo = TRUE
            LIMIT 1
            """,
            (unidade_id, spec["papel_equipe"]),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE public.school_unidade_equipe SET
                    gestor_id = %s,
                    nome = %s,
                    email = %s,
                    area_coordenacao = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    gid,
                    spec["nome"],
                    spec["email"],
                    spec["area"],
                    str(row["id"]),
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO public.school_unidade_equipe (
                    unidade_id, papel, gestor_id, nome, email, area_coordenacao
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    unidade_id,
                    spec["papel_equipe"],
                    gid,
                    spec["nome"],
                    spec["email"],
                    spec["area"],
                ),
            )


def ensure_periodo(cur, instituicao_id: str, unidade_id: str) -> str:
    rotulo = f"{ANO}.1 — Escola Teste"
    cur.execute(
        """
        SELECT id FROM public.school_periodos_letivos
        WHERE instituicao_id = %s AND unidade_id = %s AND lower(rotulo) = lower(%s)
        LIMIT 1
        """,
        (instituicao_id, unidade_id, rotulo),
    )
    row = cur.fetchone()
    if row:
        pid = str(row["id"])
        cur.execute(
            """
            UPDATE public.school_periodos_letivos SET
                status = 'em_andamento',
                em_curso = TRUE,
                ativo = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (pid,),
        )
        return pid
    cur.execute(
        """
        INSERT INTO public.school_periodos_letivos (
            instituicao_id, unidade_id, rotulo, ano_letivo,
            tipo_periodo, data_inicio, data_fim, status, em_curso, ativo
        ) VALUES (
            %s, %s, %s, %s, 'semestral',
            %s, %s, 'em_andamento', TRUE, TRUE
        )
        RETURNING id
        """,
        (
            instituicao_id,
            unidade_id,
            rotulo,
            ANO,
            date(ANO, 2, 1),
            date(ANO, 7, 15),
        ),
    )
    return str(cur.fetchone()["id"])


def ensure_curso(cur, periodo_id: str) -> str:
    nome = "Ensino Médio — Escola Teste"
    cur.execute(
        """
        SELECT id FROM public.school_cursos
        WHERE periodo_letivo_id = %s AND lower(nome) = lower(%s)
        LIMIT 1
        """,
        (periodo_id, nome),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    cur.execute(
        """
        INSERT INTO public.school_cursos (periodo_letivo_id, nome, nivel, turma_turno)
        VALUES (%s, %s, 'medio', 'manha')
        RETURNING id
        """,
        (periodo_id, nome),
    )
    return str(cur.fetchone()["id"])


def ensure_turma(
    cur,
    *,
    instituicao_id: str,
    unidade_id: str,
    periodo_id: str,
    curso_id: str,
    nome: str,
    serie: str,
    turno: str,
) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_turmas
        WHERE instituicao_id = %s AND periodo_letivo_id = %s AND lower(nome) = lower(%s)
        LIMIT 1
        """,
        (instituicao_id, periodo_id, nome),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    cur.execute(
        """
        INSERT INTO public.school_turmas (
            instituicao_id, nome, serie_ano, turno, ano_letivo,
            unidade_id, periodo_letivo_id, curso_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            instituicao_id,
            nome,
            serie,
            turno,
            ANO,
            unidade_id,
            periodo_id,
            curso_id,
        ),
    )
    return str(cur.fetchone()["id"])


def ensure_disciplina(cur, instituicao_id: str, curso_id: str, nome: str) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_disciplinas
        WHERE instituicao_id = %s AND lower(nome) = lower(%s)
        LIMIT 1
        """,
        (instituicao_id, nome),
    )
    row = cur.fetchone()
    if row:
        did = str(row["id"])
    else:
        cur.execute(
            """
            INSERT INTO public.school_disciplinas (
                instituicao_id, nome, ementa, carga_horaria_horas
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                instituicao_id,
                nome,
                f"Ementa fictícia — {nome} (Escola Teste)",
                80,
            ),
        )
        did = str(cur.fetchone()["id"])
    cur.execute(
        """
        INSERT INTO public.school_curso_disciplinas (curso_id, disciplina_id)
        VALUES (%s, %s)
        ON CONFLICT (curso_id, disciplina_id) DO NOTHING
        """,
        (curso_id, did),
    )
    return did


def ensure_aluno(
    cur,
    *,
    instituicao_id: str,
    turma_id: str,
    nome: str,
    matricula: str,
) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_alunos
        WHERE instituicao_id = %s AND matricula = %s
        LIMIT 1
        """,
        (instituicao_id, matricula),
    )
    row = cur.fetchone()
    if row:
        aid = str(row["id"])
        cur.execute(
            """
            UPDATE public.school_alunos
            SET nome = %s, turma_id = %s, ativo = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (nome, turma_id, aid),
        )
        return aid
    cur.execute(
        """
        INSERT INTO public.school_alunos (
            instituicao_id, nome, matricula, turma_id, data_nascimento
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (instituicao_id, nome, matricula, turma_id, date(2010, 3, 15)),
    )
    return str(cur.fetchone()["id"])


def invite_professor(cur, instituicao_id: str, email: str) -> dict:
    email = email.lower()
    b2c_id = _provisional_b2c_id(email)
    cur.execute(
        """
        SELECT id, status_vinculo, professor_b2c_id, email_convite
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s
          AND (
            lower(email_convite) = %s
            OR professor_b2c_id = %s
          )
        LIMIT 1
        """,
        (instituicao_id, email, b2c_id),
    )
    existing = cur.fetchone()
    if existing and existing["status_vinculo"] != "revogado":
        return {
            "id": str(existing["id"]),
            "status_vinculo": existing["status_vinculo"],
            "email": email,
            "created": False,
            "professor_b2c_id": existing["professor_b2c_id"],
        }
    if existing and existing["status_vinculo"] == "revogado":
        cur.execute(
            """
            UPDATE public.school_professores_vinculo
            SET email_convite = %s,
                professor_b2c_id = %s,
                status_vinculo = 'pendente',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, status_vinculo, professor_b2c_id
            """,
            (email, b2c_id, str(existing["id"])),
        )
    else:
        cur.execute(
            """
            INSERT INTO public.school_professores_vinculo
                (instituicao_id, professor_b2c_id, email_convite, status_vinculo)
            VALUES (%s, %s, %s, 'pendente')
            RETURNING id, status_vinculo, professor_b2c_id
            """,
            (instituicao_id, b2c_id, email),
        )
    row = cur.fetchone()
    return {
        "id": str(row["id"]),
        "status_vinculo": row["status_vinculo"],
        "email": email,
        "created": True,
        "professor_b2c_id": row["professor_b2c_id"],
    }


def push_teacher_invite(instituicao_id: str, vinculo: dict, razao: str) -> dict:
    email = vinculo["email"]
    invite_url = _invite_url(email)
    return dispatch_event_to_b2c(
        "TEACHER_INVITE",
        {
            "instituicao_id": instituicao_id,
            "instituicao_nome": razao,
            "vinculo_id": vinculo["id"],
            "professor_email": email,
            "email": email,
            "professor_b2c_id": str(vinculo.get("professor_b2c_id") or ""),
            "invite_url": invite_url,
        },
    )


def ensure_alocacao(
    cur,
    *,
    instituicao_id: str,
    unidade_id: str,
    periodo_id: str,
    disciplina_id: str,
    professor_vinculo_id: str,
    turma_id: str,
) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_alocacoes_docentes
        WHERE instituicao_id = %s
          AND unidade_id = %s
          AND periodo_id = %s
          AND disciplina_id = %s
          AND professor_vinculo_id = %s
          AND turma_id IS NOT DISTINCT FROM %s
        LIMIT 1
        """,
        (
            instituicao_id,
            unidade_id,
            periodo_id,
            disciplina_id,
            professor_vinculo_id,
            turma_id,
        ),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    cur.execute(
        """
        INSERT INTO public.school_alocacoes_docentes (
            instituicao_id, unidade_id, periodo_id,
            disciplina_id, professor_vinculo_id, turma_id
        ) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            instituicao_id,
            unidade_id,
            periodo_id,
            disciplina_id,
            professor_vinculo_id,
            turma_id,
        ),
    )
    return str(cur.fetchone()["id"])


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_teacher_allocated_payload(cur, aloc_id: str) -> dict:
    """Mesmo shape de secretaria_routes._build_teacher_allocated_payload."""
    cur.execute(
        """
        SELECT
            a.id AS alocacao_id,
            a.instituicao_id,
            i.razao_social AS instituicao_nome,
            u.id AS unidade_id,
            u.nome AS unidade_nome,
            p.id AS periodo_id,
            p.rotulo AS periodo_nome,
            p.data_inicio,
            p.data_fim,
            p.tipo_periodo,
            d.id AS disciplina_id,
            d.nome AS disciplina_nome,
            d.ementa,
            v.id AS vinculo_id,
            v.email_convite,
            v.professor_b2c_id,
            t.id AS turma_id,
            t.nome AS turma_nome,
            t.turno AS turma_turno,
            t.curso_id,
            c.nome AS curso_nome
        FROM public.school_alocacoes_docentes a
        JOIN public.school_instituicoes i ON i.id = a.instituicao_id
        JOIN public.school_unidades u ON u.id = a.unidade_id
        JOIN public.school_periodos_letivos p ON p.id = a.periodo_id
        JOIN public.school_disciplinas d ON d.id = a.disciplina_id
        JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
        LEFT JOIN public.school_turmas t ON t.id = a.turma_id
        LEFT JOIN public.school_cursos c ON c.id = t.curso_id
        WHERE a.id = %s
        """,
        (aloc_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"alocação {aloc_id} não encontrada")

    payload: dict = {
        "professor_b2c_id": str(row["professor_b2c_id"]),
        "disciplina_nome": row["disciplina_nome"],
        "ementa_macro": row.get("ementa") or "",
        "data_inicio_periodo": _iso(row.get("data_inicio")),
        "data_fim_periodo": _iso(row.get("data_fim")),
        "tipo_periodo": row.get("tipo_periodo") or "semestral",
        "instituicao_id": str(row["instituicao_id"]),
        "instituicao_nome": (row.get("instituicao_nome") or "").strip() or None,
        "unidade_id": str(row["unidade_id"]),
        "unidade_nome": row["unidade_nome"],
        "periodo_id": str(row["periodo_id"]),
        "periodo_nome": row["periodo_nome"],
        "disciplina_id": str(row["disciplina_id"]),
        "alocacao_id": str(row["alocacao_id"]),
        "professor_email": row.get("email_convite"),
        "vinculo_id": str(row["vinculo_id"]) if row.get("vinculo_id") else None,
    }
    if row.get("curso_id"):
        payload["curso_id"] = str(row["curso_id"])
        payload["curso_nome"] = (row.get("curso_nome") or "").strip() or "Curso"
    if row.get("turma_id"):
        payload["turma_id"] = str(row["turma_id"])
        payload["turma_nome"] = row["turma_nome"]
        if row.get("turma_turno"):
            payload["turma_turno"] = row["turma_turno"]
    return payload


def mark_alocacao_notificado(aloc_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.school_alocacoes_docentes
                SET notificado_b2c = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (aloc_id,),
            )


def push_teacher_allocated(aloc_id: str) -> dict:
    """Caminho real da Secretaria: dispatch_teacher_allocated + notificado_b2c."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            payload = build_teacher_allocated_payload(cur, aloc_id)
    try:
        dispatch = dispatch_teacher_allocated(payload)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "alocacao_id": aloc_id}
    if dispatch.get("ok"):
        mark_alocacao_notificado(aloc_id)
    return {
        "ok": bool(dispatch.get("ok")),
        "alocacao_id": aloc_id,
        "professor_email": payload.get("professor_email"),
        "b2c": {k: v for k, v in dispatch.items() if k != "response"},
        "b2c_response": dispatch.get("response"),
    }


def main() -> int:
    print("=== seed Escola Teste (produção) ===", flush=True)
    print(f"dominio={DOMINIO} sku={SKU} order_id={ORDER_ID}", flush=True)

    inst_id, provision_meta = ensure_instituicao_e_plano()
    print(json.dumps({"provision": provision_meta}, default=str, ensure_ascii=False), flush=True)

    credentials: list[dict] = []
    report: dict = {"instituicao_id": inst_id}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            gestores_map: dict[str, str] = {}
            for spec in GESTORES:
                gid, pwd = upsert_gestor(cur, instituicao_id=inst_id, spec=spec)
                gestores_map[spec["email"]] = gid
                credentials.append(
                    {
                        "email": spec["email"],
                        "zona": spec["zona"],
                        "gestor_id": gid,
                        "password": pwd,  # None se já existia
                        "password_status": "gerada" if pwd else "inalterada (já existia)",
                    }
                )

            unidade_id = ensure_unidade(cur, inst_id)
            ensure_equipe(cur, unidade_id, gestores_map)
            periodo_id = ensure_periodo(cur, inst_id, unidade_id)
            curso_id = ensure_curso(cur, periodo_id)
            turma1 = ensure_turma(
                cur,
                instituicao_id=inst_id,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_id,
                nome="1ª Série A — Escola Teste",
                serie="1ª série",
                turno="manha",
            )
            turma2 = ensure_turma(
                cur,
                instituicao_id=inst_id,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_id,
                nome="1ª Série B — Escola Teste",
                serie="1ª série",
                turno="tarde",
            )
            disc1 = ensure_disciplina(cur, inst_id, curso_id, "Matemática — Escola Teste")
            disc2 = ensure_disciplina(cur, inst_id, curso_id, "Português — Escola Teste")

            alunos = [
                ensure_aluno(
                    cur,
                    instituicao_id=inst_id,
                    turma_id=turma1,
                    nome="Aluno Teste Ana",
                    matricula="ET-2026-001",
                ),
                ensure_aluno(
                    cur,
                    instituicao_id=inst_id,
                    turma_id=turma1,
                    nome="Aluno Teste Bruno",
                    matricula="ET-2026-002",
                ),
                ensure_aluno(
                    cur,
                    instituicao_id=inst_id,
                    turma_id=turma2,
                    nome="Aluno Teste Carla",
                    matricula="ET-2026-003",
                ),
            ]

            invites = []
            for email in PROFESSORES:
                invites.append(invite_professor(cur, inst_id, email))

            # commit vínculos antes do push B2C
            report.update(
                {
                    "unidade_id": unidade_id,
                    "periodo_id": periodo_id,
                    "curso_id": curso_id,
                    "turmas": {"turma1": turma1, "turma2": turma2},
                    "disciplinas": {"matematica": disc1, "portugues": disc2},
                    "alunos": alunos,
                    "gestores": {e: gestores_map[e] for e in gestores_map},
                    "convites_pre_push": [
                        {
                            "email": i["email"],
                            "vinculo_id": i["id"],
                            "status": i["status_vinculo"],
                            "created": i["created"],
                        }
                        for i in invites
                    ],
                }
            )

    # Push TEACHER_INVITE (mesmo caminho de Minha Equipe / disparar-convite)
    push_results = []
    for inv in invites:
        if inv["status_vinculo"] == "ativo":
            push_results.append(
                {
                    "email": inv["email"],
                    "skipped_push": True,
                    "reason": "já ativo",
                    "b2c": None,
                }
            )
            continue
        b2c = push_teacher_invite(inst_id, inv, RAZAO)
        push_results.append({"email": inv["email"], "b2c": b2c})

    # Alocações + status final dos convites
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Re-lê status (B2C pode ter aceitado se conta Inove já existia)
            final_invites = []
            for inv in invites:
                cur.execute(
                    """
                    SELECT id, email_convite, status_vinculo, professor_b2c_id
                    FROM public.school_professores_vinculo WHERE id = %s
                    """,
                    (inv["id"],),
                )
                row = cur.fetchone()
                final_invites.append(dict(row) if row else inv)

            # Map email → vinculo
            by_email = {str(r["email_convite"]).lower(): r for r in final_invites}
            p1 = by_email.get(PROFESSORES[0].lower())
            p2 = by_email.get(PROFESSORES[1].lower())
            aloc1 = aloc2 = None
            if p1:
                aloc1 = ensure_alocacao(
                    cur,
                    instituicao_id=inst_id,
                    unidade_id=report["unidade_id"],
                    periodo_id=report["periodo_id"],
                    disciplina_id=report["disciplinas"]["matematica"],
                    professor_vinculo_id=str(p1["id"]),
                    turma_id=report["turmas"]["turma1"],
                )
            if p2:
                aloc2 = ensure_alocacao(
                    cur,
                    instituicao_id=inst_id,
                    unidade_id=report["unidade_id"],
                    periodo_id=report["periodo_id"],
                    disciplina_id=report["disciplinas"]["portugues"],
                    professor_vinculo_id=str(p2["id"]),
                    turma_id=report["turmas"]["turma2"],
                )

            cur.execute(
                """
                SELECT total_assentos, assentos_em_uso, sku_ultimo
                FROM public.school_licencas WHERE instituicao_id = %s
                """,
                (inst_id,),
            )
            lic_final = cur.fetchone()

    # TEACHER_ALLOCATED — mesmo caminho da Secretaria (pendente no B2C até o aceite)
    aloc_pushes = []
    for aloc_id in (aloc1, aloc2):
        if aloc_id:
            aloc_pushes.append(push_teacher_allocated(aloc_id))

    report["convites_finais"] = [
        {
            "email": r.get("email_convite"),
            "vinculo_id": str(r["id"]),
            "status_vinculo": r.get("status_vinculo"),
            "professor_b2c_id": r.get("professor_b2c_id"),
        }
        for r in final_invites
    ]
    report["alocacoes"] = {"prof1_mat_turma1": aloc1, "prof2_port_turma2": aloc2}
    report["teacher_allocated_pushes"] = aloc_pushes
    report["pushes"] = push_results
    report["licencas_final"] = dict(lic_final) if lic_final else None
    report["equipe_mapeamento"] = [
        {
            "email": s["email"],
            "zona_rbac": s["zona"],
            "papel_unidade": s["papel_equipe"],
            "area": s["area"],
        }
        for s in GESTORES
    ]

    print("--- REPORT ---", flush=True)
    print(json.dumps(report, default=str, ensure_ascii=False, indent=2), flush=True)

    print("--- CREDENTIALS (não versionar) ---", flush=True)
    for c in credentials:
        line = {
            "email": c["email"],
            "zona": c["zona"],
            "gestor_id": c["gestor_id"],
            "password_status": c["password_status"],
        }
        if c["password"]:
            line["password"] = c["password"]
        print(json.dumps(line, ensure_ascii=False), flush=True)

    print("=== seed OK ===", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SEED_FAILED: {exc}", file=sys.stderr, flush=True)
        raise
