#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PanelDX — Seed de demonstração (local ou RDS de produção)

Recria contas de teste padronizadas, removendo **somente** os dados
vinculados a esses usuários (não apaga outros clientes do banco):

  • Sysadmin  : sysadmin@leaction.com.br  (senha — SEED_TEAM_PASSWORD)
  • Executor  : executor@paneldx.com.br    (senha — SEED_TEAM_PASSWORD)
  • Lead demo : sistema@paneldx.com.br    (código LA-PANEL1)

Estágios do funil (parâmetro 1–4):

  1 — Primeiro login (Insight Gate)              → AGUARDANDO CONTEXTO
  2 — Pós avaliação inicial                      → PRESURVEY OK
  3 — Pós avaliação completa                     → AVALIACAO OK
  4 — Pós plano geral (Kanban mock)              → CONCLUIDO

Uso local:
  python seed_dev_client.py 1

Uso produção (RDS — só reseta os 3 usuários demo):
  SEED_DEV_ALLOW=1 SEED_PROD_CONFIRM=paneldx-demo-users python seed_dev_client.py 1

Uso produção (RDS — só sistema@paneldx.com.br e dados do cliente dele):
  SEED_DEV_ALLOW=1 SEED_PROD_CONFIRM=paneldx-demo-lead python seed_dev_client.py 1 --lead-only

  Ou: .\\scripts\\deploy\\12-seed-prod-lead-only.ps1 -Stage 1 -ConfirmLeadReset -ViaEc2

Reset total da base (apenas local, opcional):
  python seed_dev_client.py 1 --full-reset

Requer PostgreSQL e variáveis DB_* em LeAction_SysF/.env ou .env na raiz.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor, execute_batch

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "LeAction_SysF"

DEV_EMAIL = "sistema@paneldx.com.br"
DEV_ACCESS_CODE = "LA-PANEL1"
DEV_CLIENT_NAME = "Escola Sistema PanelDX"
DEV_COMPANY = "Colégio Sistema PanelDX"

SYSADMIN_EMAIL = "sysadmin@leaction.com.br"
EXECUTOR_EMAIL = "executor@paneldx.com.br"
DEFAULT_TEAM_PASSWORD = "PanelDX1!"

DEMO_TEAM_EMAILS = (SYSADMIN_EMAIL.lower(), EXECUTOR_EMAIL.lower())

# TRUNCATE global — apenas com --full-reset (dev local)
FULL_TRUNCATE_STATEMENTS = [
    "TRUNCATE TABLE public.ctdi_sprn RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_itera RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_projetos RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_surv RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_main RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_matu RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_clie RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_lead_access RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_matu_presurvey RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_squads RESTART IDENTITY CASCADE",
    "TRUNCATE TABLE public.ctdi_team RESTART IDENTITY CASCADE",
]


def get_team_passwords() -> tuple[str, str]:
    default = (os.getenv("SEED_TEAM_PASSWORD") or DEFAULT_TEAM_PASSWORD).strip()
    sys_p = (os.getenv("SEED_SYSADMIN_PASSWORD") or default).strip()
    exe_p = (os.getenv("SEED_EXECUTOR_PASSWORD") or default).strip()
    if not sys_p or not exe_p:
        raise SystemExit(
            "SEED_SYSADMIN_PASSWORD / SEED_EXECUTOR_PASSWORD não podem ser vazios."
        )
    return sys_p, exe_p


def hash_password(plain: str) -> str:
    from werkzeug.security import generate_password_hash

    return generate_password_hash(plain)


def _infer_system_role(role_db: str | None, position: str | None) -> str:
    role_up = (role_db or "").upper().strip()
    pos = position or ""
    if role_up in ("ADMIN", "SYSADMIN"):
        return "sysadmin"
    if role_up == "CONSULTOR" or "Consultor Estratégico" in pos:
        return "consultor"
    if role_up == "LEAD":
        return "led"
    if "Analista" in pos or role_up == "EXECUTOR":
        return "executor"
    return "executor"


def _scalar(row) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()), None)
    return row[0]


def _table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    return bool(_scalar(cur.fetchone()))


def _delete_where(cur, table: str, column: str, value) -> None:
    if not _table_exists(cur, table):
        return
    cur.execute(f"DELETE FROM public.{table} WHERE {column} = %s", (value,))


def _purge_paneldx_usuario_by_email(cur, email: str) -> None:
    if not _table_exists(cur, "paneldx_usuarios"):
        return
    cur.execute(
        """
        SELECT id_usuario FROM public.paneldx_usuarios
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        """,
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return
    id_usuario = _scalar(row) if not isinstance(row, dict) else row["id_usuario"]
    _delete_where(cur, "notificacoes", "user_id", id_usuario)
    _delete_where(cur, "consultor_associacoes", "user_id", id_usuario)
    cur.execute("DELETE FROM public.paneldx_usuarios WHERE id_usuario = %s", (id_usuario,))


def _purge_okr_for_client(cur, id_clie: int) -> None:
    if not _table_exists(cur, "ctdi_okr_direcionadores"):
        return
    cur.execute(
        """
        DELETE FROM public.ctdi_okr_atividades
        WHERE id_kr IN (
            SELECT k.id_kr
            FROM public.ctdi_okr_krs k
            JOIN public.ctdi_okr_objetivos_dt o ON o.id_obj_dt = k.id_obj_dt
            JOIN public.ctdi_okr_direcionadores d ON d.id_direc = o.id_direc
            WHERE d.id_clie = %s
        )
        """,
        (id_clie,),
    )
    cur.execute(
        """
        DELETE FROM public.ctdi_okr_krs
        WHERE id_obj_dt IN (
            SELECT o.id_obj_dt
            FROM public.ctdi_okr_objetivos_dt o
            JOIN public.ctdi_okr_direcionadores d ON d.id_direc = o.id_direc
            WHERE d.id_clie = %s
        )
        """,
        (id_clie,),
    )
    cur.execute(
        """
        DELETE FROM public.ctdi_okr_objetivos_dt
        WHERE id_direc IN (
            SELECT id_direc FROM public.ctdi_okr_direcionadores WHERE id_clie = %s
        )
        """,
        (id_clie,),
    )
    _delete_where(cur, "ctdi_okr_comentarios", "id_clie", id_clie)
    _delete_where(cur, "ctdi_okr_direcionadores", "id_clie", id_clie)


def _purge_kanban_for_client(cur, id_clie: int) -> None:
    cur.execute("SELECT id_proj FROM public.ctdi_projetos WHERE id_clie = %s", (id_clie,))
    for row in cur.fetchall():
        id_proj = _scalar(row)
        _delete_where(cur, "ctdi_squads", "id_proj", id_proj)
    _delete_where(cur, "ctdi_projetos", "id_clie", id_clie)

    cur.execute(
        """
        SELECT m.id_ctdi FROM public.ctdi_main m
        JOIN public.ctdi_matu ma ON ma.id_matu = m.id_matu
        WHERE ma.id_clie = %s
        """,
        (id_clie,),
    )
    ctdi_ids = [_scalar(r) for r in cur.fetchall()]
    for id_ctdi in ctdi_ids:
        cur.execute(
            "SELECT id_itera FROM public.ctdi_itera WHERE id_ctdi = %s", (id_ctdi,)
        )
        for row in cur.fetchall():
            id_itera = _scalar(row)
            _delete_where(cur, "ctdi_sprn", "id_itera", id_itera)
        cur.execute("DELETE FROM public.ctdi_itera WHERE id_ctdi = %s", (id_ctdi,))
        cur.execute("DELETE FROM public.ctdi_main WHERE id_ctdi = %s", (id_ctdi,))


def _purge_matu_chain(cur, id_clie: int) -> None:
    cur.execute("SELECT id_matu FROM public.ctdi_matu WHERE id_clie = %s", (id_clie,))
    matu_ids = [_scalar(r) for r in cur.fetchall()]
    for id_matu in matu_ids:
        _delete_where(cur, "agenda_eventos", "id_matu", id_matu)
        _delete_where(cur, "ctdi_surv", "id_matu", id_matu)
        _delete_where(cur, "ctdi_matu_presurvey", "id_matu", id_matu)
    for id_matu in matu_ids:
        cur.execute("DELETE FROM public.ctdi_matu WHERE id_matu = %s", (id_matu,))


def purge_demo_lead(cur, email: str = DEV_EMAIL) -> None:
    cur.execute(
        """
        SELECT id_clie FROM public.ctdi_clie
        WHERE LOWER(TRIM(mail_clie)) = LOWER(TRIM(%s))
        """,
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return
    id_clie = _scalar(row) if not isinstance(row, dict) else row["id_clie"]
    print(f"    -> lead {email} (id_clie={id_clie})")

    _purge_kanban_for_client(cur, id_clie)
    _purge_matu_chain(cur, id_clie)
    _purge_okr_for_client(cur, id_clie)
    # eSIM: eventos de telemetria e backlog NÃO são apagados no reset demo
    # (catálogo global e histórico de testes administrativos permanecem).
    _delete_where(cur, "ctdi_lead_access", "id_clie", id_clie)
    _delete_where(cur, "consultor_associacoes", "client_id", id_clie)
    _purge_paneldx_usuario_by_email(cur, email)
    cur.execute("DELETE FROM public.ctdi_clie WHERE id_clie = %s", (id_clie,))


def purge_team_demo_user(cur, email: str) -> None:
    cur.execute(
        """
        SELECT id_member, id_usuario FROM public.ctdi_team
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        """,
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return
    id_member = row["id_member"] if isinstance(row, dict) else row[0]
    print(f"    -> equipe {email} (id_member={id_member})")

    if _table_exists(cur, "ctdi_okr_atividades"):
        cur.execute(
            """
            UPDATE public.ctdi_okr_atividades
            SET executor_id = NULL
            WHERE executor_id = %s
            """,
            (id_member,),
        )
    cur.execute("DELETE FROM public.ctdi_team WHERE id_member = %s", (id_member,))
    _purge_paneldx_usuario_by_email(cur, email)


def reset_demo_accounts(cur) -> None:
    print("==> Removendo apenas dados dos usuarios demo...")
    purge_demo_lead(cur, DEV_EMAIL)
    purge_team_demo_user(cur, SYSADMIN_EMAIL)
    purge_team_demo_user(cur, EXECUTOR_EMAIL)


def reset_lead_only(cur) -> None:
    print(f"==> Removendo apenas dados de {DEV_EMAIL}...")
    purge_demo_lead(cur, DEV_EMAIL)


def _truncate_if_exists(cur, table: str) -> None:
    if _table_exists(cur, table):
        cur.execute(f"TRUNCATE TABLE public.{table} RESTART IDENTITY CASCADE")


def reset_database_full(cur) -> None:
    print("==> Limpando base INTEIRA (TRUNCATE — apenas --full-reset)...")
    for table in ("notificacoes", "consultor_associacoes"):
        _truncate_if_exists(cur, table)
    for stmt in FULL_TRUNCATE_STATEMENTS:
        cur.execute(stmt)
    _truncate_if_exists(cur, "paneldx_usuarios")


def load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (ROOT / ".env", BACKEND_DIR / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def get_db_config() -> dict:
    load_env_files()
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME", "LeAction_SysF")
    user = os.getenv("DB_USER") or os.getenv("DB_USERNAME", "postgres")
    password = os.getenv("DB_PASS") or os.getenv("DB_PASSWORD", "")
    sslmode = os.getenv("DB_SSLMODE", "disable")

    if not password:
        raise SystemExit(
            "DB_PASS não definido. Configure LeAction_SysF/.env antes de rodar o seed."
        )

    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
        "sslmode": sslmode,
    }


def assert_environment(cfg: dict, *, lead_only: bool = False) -> str:
    host = (cfg.get("host") or "").lower()
    is_local = host in ("127.0.0.1", "localhost", "::1")

    if is_local:
        return "local"

    if os.getenv("SEED_DEV_ALLOW", "").strip() != "1":
        raise SystemExit(
            f"Abortado: DB_HOST={host!r} não é local. "
            "Defina SEED_DEV_ALLOW=1 para RDS/produção."
        )

    confirm = os.getenv("SEED_PROD_CONFIRM", "").strip()
    if lead_only:
        allowed = ("paneldx-demo-lead", "paneldx-demo-reset")
        hint = "paneldx-demo-lead (remove somente sistema@paneldx.com.br e dados do cliente)."
    else:
        allowed = ("paneldx-demo-users", "paneldx-demo-reset")
        hint = (
            "paneldx-demo-users (remove os 3 usuarios demo: lead, sysadmin, executor) "
            "ou paneldx-demo-lead com --lead-only."
        )
    if confirm not in allowed:
        raise SystemExit(f"Abortado: RDS exige SEED_PROD_CONFIRM={hint}")

    if "rds.amazonaws.com" in host:
        if cfg.get("sslmode") in (None, "", "disable"):
            cfg["sslmode"] = "require"
        print(f"⚠️  ALVO RDS: {host} (sslmode={cfg['sslmode']})")

    return "remote"


def connect_db(cfg: dict):
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode=cfg.get("sslmode", "disable"),
    )


def seed_team_accounts(cur) -> None:
    sys_p, exe_p = get_team_passwords()
    sys_hash = hash_password(sys_p)
    exe_hash = hash_password(exe_p)
    print("==> Recriando SysAdmin e Executor (ctdi_team)...")
    accounts = (
        (SYSADMIN_EMAIL.lower(), "SysAdmin LeAction", "ADMIN", None, sys_hash),
        (
            EXECUTOR_EMAIL.lower(),
            "Executor PanelDX (Teste)",
            "CLIENTE",
            "Analista Executor",
            exe_hash,
        ),
    )
    for email, nome, role, position, pwd_hash in accounts:
        cur.execute(
            """
            INSERT INTO ctdi_team (
                nome, email, role, ativo, data_cadastro, password_hash, position
            ) VALUES (%s, %s, %s, true, NOW(), %s, %s)
            RETURNING id_member
            """,
            (nome, email, role, pwd_hash, position),
        )


def _upsert_paneldx_usuario(
    cur,
    *,
    email: str,
    nome: str,
    system_role: str,
    password_hash: str | None,
    id_clie: int | None = None,
) -> int | None:
    if not _table_exists(cur, "paneldx_usuarios"):
        return None
    cur.execute(
        """
        SELECT id_usuario FROM public.paneldx_usuarios
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        """,
        (email,),
    )
    row = cur.fetchone()
    if row:
        id_usuario = _scalar(row) if not isinstance(row, dict) else row["id_usuario"]
        cur.execute(
            """
            UPDATE public.paneldx_usuarios
            SET nome = %s,
                password_hash = COALESCE(%s, password_hash),
                system_role = %s,
                id_clie = %s,
                ativo = true
            WHERE id_usuario = %s
            """,
            (nome, password_hash, system_role, id_clie, id_usuario),
        )
        return id_usuario
    cur.execute(
        """
        INSERT INTO public.paneldx_usuarios (
            email, nome, password_hash, system_role, id_clie, ativo
        ) VALUES (%s, %s, %s, %s, %s, true)
        RETURNING id_usuario
        """,
        (email.lower(), nome, password_hash, system_role, id_clie),
    )
    inserted = cur.fetchone()
    return inserted["id_usuario"] if isinstance(inserted, dict) else inserted[0]


def sync_paneldx_usuarios(cur, id_clie: int) -> None:
    if not _table_exists(cur, "paneldx_usuarios"):
        return

    print("==> Sincronizando paneldx_usuarios (RBAC - apenas contas demo)...")
    for demo_email in DEMO_TEAM_EMAILS:
        cur.execute(
            """
            SELECT id_member, nome, email, role, position, password_hash
            FROM ctdi_team
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (demo_email,),
        )
        row = cur.fetchone()
        if not row:
            continue
        email = row["email"].strip().lower()
        system_role = _infer_system_role(row["role"], row["position"])
        id_usuario = _upsert_paneldx_usuario(
            cur,
            email=email,
            nome=row["nome"],
            system_role=system_role,
            password_hash=row["password_hash"],
        )
        if id_usuario:
            cur.execute(
                "UPDATE ctdi_team SET id_usuario = %s WHERE id_member = %s",
                (id_usuario, row["id_member"]),
            )

    _upsert_paneldx_usuario(
        cur,
        email=DEV_EMAIL.lower(),
        nome=DEV_CLIENT_NAME,
        system_role="led",
        password_hash=None,
        id_clie=id_clie,
    )


def create_dev_client(cur) -> tuple[int, int]:
    print(f"==> Criando cliente {DEV_EMAIL}...")
    cur.execute(
        """
        INSERT INTO ctdi_clie (
            nome_clie, mail_clie, docu_clie, fone_clie, empresa_clie, init_role, has_active_project
        ) VALUES (%s, %s, %s, %s, %s, %s, false)
        RETURNING id_clie
        """,
        (
            DEV_CLIENT_NAME,
            DEV_EMAIL.lower(),
            "00.000.000/0001-99",
            "(85) 99999-0000",
            DEV_COMPANY,
            "GENERAL",
        ),
    )
    id_clie = cur.fetchone()["id_clie"]

    cur.execute(
        """
        INSERT INTO ctdi_matu (
            id_clie, status_ia,
            pdom_pres, pdim_pres, pgen_pres,
            pdom_fut, pdim_fut, pgen_fut,
            pdom_gap, pdim_gap, pgen_gap
        ) VALUES (
            %s, 'AGUARDANDO CONTEXTO',
            '{}'::jsonb, '{}'::jsonb, 0,
            '{}'::jsonb, '{}'::jsonb, 0,
            '{}'::jsonb, '{}'::jsonb, 0
        )
        RETURNING id_matu
        """,
        (id_clie,),
    )
    id_matu = cur.fetchone()["id_matu"]

    cur.execute(
        """
        INSERT INTO ctdi_lead_access (id_clie, access_code)
        VALUES (%s, %s)
        """,
        (id_clie, DEV_ACCESS_CODE),
    )
    return id_clie, id_matu


def fetch_questions(cur, presurvey_only: bool = False) -> list[dict]:
    if presurvey_only:
        cur.execute(
            """
            SELECT id_ques, id_dime, id_doma, prefu_ques, setor_ques
            FROM ctdi_quest
            WHERE presurvey_ques = true
              AND id_dime IS NOT NULL AND id_doma IS NOT NULL
            ORDER BY id_ques
            """
        )
    else:
        cur.execute(
            """
            SELECT id_ques, id_dime, id_doma, prefu_ques, setor_ques
            FROM ctdi_quest
            WHERE id_dime IS NOT NULL AND id_doma IS NOT NULL
            ORDER BY id_ques
            """
        )
    return list(cur.fetchall())


def insert_random_survey_answers(cur, id_matu: int, presurvey_only: bool = False) -> int:
    questions = fetch_questions(cur, presurvey_only=presurvey_only)
    if not questions:
        raise RuntimeError(
            "Nenhuma questão encontrada em ctdi_quest. "
            "O catálogo de perguntas precisa existir no banco."
        )

    rows = []
    for q in questions:
        grade = random.randint(1, 5)
        rows.append((id_matu, q["id_ques"], q["id_dime"], q["id_doma"], grade))

    execute_batch(
        cur,
        """
        INSERT INTO ctdi_surv (id_matu, id_ques, id_dime, id_doma, grad_ques)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id_matu, id_ques) DO UPDATE SET
            grad_ques = EXCLUDED.grad_ques,
            id_dime = EXCLUDED.id_dime,
            id_doma = EXCLUDED.id_doma
        """,
        rows,
    )
    return len(rows)


def _media(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_presurvey_calculation(cur, id_matu: int) -> None:
    """Replica a lógica de /api/calculate-presurvey."""
    cur.execute(
        """
        SELECT q.id_dime, q.id_doma, q.prefu_ques, s.grad_ques
        FROM ctdi_surv s
        JOIN ctdi_quest q ON s.id_ques = q.id_ques
        WHERE s.id_matu = %s AND q.presurvey_ques = true
        """,
        (id_matu,),
    )
    respostas = cur.fetchall()

    cur.execute(
        """
        SELECT id_dime, id_doma,
               AVG((lower(grad_refb) + upper(grad_refb)) / 2.0) AS media_setor
        FROM ctdi_refb
        WHERE UPPER(setr_refb) IN ('EDUCACAO', 'EDUCAÇÃO', 'EDUCACIONAL', 'SETOR EDUCACAO')
        GROUP BY id_dime, id_doma
        """
    )
    bench_map = {
        (int(r["id_dime"]), int(r["id_doma"])): float(r["media_setor"])
        for r in cur.fetchall()
        if r["id_dime"] is not None and r["id_doma"] is not None
    }

    stats_dime = {i: {"P": [], "F": []} for i in range(1, 6)}
    stats_doma: dict[tuple[int, int], dict[str, list[float]]] = {}

    for row in respostas:
        d_id, doma_id, prefu, nota = (
            row["id_dime"],
            row["id_doma"],
            row["prefu_ques"],
            row["grad_ques"],
        )
        if nota is None or d_id is None or doma_id is None:
            continue
        n = float(nota)
        prefu_key = (prefu or "P").upper()
        stats_dime[int(d_id)][prefu_key].append(n)
        key = (int(d_id), int(doma_id))
        stats_doma.setdefault(key, {"P": [], "F": []})[prefu_key].append(n)

    nomes_dimensoes = {
        1: "Estratégica",
        2: "Humana",
        3: "Organizacional",
        4: "Pedagógica",
        5: "Tecnológica",
    }
    nomes_dominios = {
        1: "Estratégia Digital",
        2: "Modelo de Negócio Digital",
        3: "Cultura de Inovação",
        4: "Cultura de Dados",
        5: "Cultura de Colaboração",
        6: "Governança Digital",
        7: "Plataformas Digitais",
        8: "Capacidades Digitais",
        9: "Métricas Digitais",
    }

    scores_dominios_json = {}
    for key, vals in stats_doma.items():
        id_dime, id_doma = key
        nome = f"{nomes_dimensoes.get(id_dime, f'Dim {id_dime}')} - {nomes_dominios.get(id_doma, f'Dom {id_doma}')}"
        scores_dominios_json[nome] = {
            "P": round(_media(vals["P"]), 2),
            "F": round(_media(vals["F"]), 2),
            "M": round(bench_map.get(key, 0.0), 2),
        }

    gap_ambicao_max = -1.0
    par_ambicao = (1, 1)
    gap_mercado_max = -1.0
    par_mercado = (1, 1)

    for key, vals in stats_doma.items():
        med_p = _media(vals["P"])
        med_f = _media(vals["F"])
        med_m = bench_map.get(key, 0.0)
        g_amb = med_f - med_p
        if g_amb > gap_ambicao_max:
            gap_ambicao_max = g_amb
            par_ambicao = key
        g_mkt = med_m - med_p
        if g_mkt > gap_mercado_max:
            gap_mercado_max = g_mkt
            par_mercado = key

    def tech_info(dime, doma):
        cur.execute(
            """
            SELECT b.name_bloc, b.desc_bloc, d.name_derv, d.desc_derv
            FROM leaf_bloc b
            JOIN leaf_derv d ON b.id_bloc = d.id_bloc
            WHERE b.id_dime = %s AND b.id_doma = %s
            ORDER BY b.level_bloc ASC
            LIMIT 1
            """,
            (dime, doma),
        )
        row = cur.fetchone()
        return row if row else {
            "name_bloc": "Iniciativa Digital",
            "desc_bloc": "Sem descrição",
            "name_derv": "Plano de Ação",
            "desc_derv": "Sem descrição",
        }

    inf_amb = tech_info(*par_ambicao)
    inf_mkt = tech_info(*par_mercado)
    insights_data = {
        "recomendas": {
            "ambicao": {
                "id": par_ambicao,
                "bloco": inf_amb["name_bloc"],
                "desc_b": inf_amb["desc_bloc"],
                "derv": inf_amb["name_derv"],
                "desc_d": inf_amb["desc_derv"],
            },
            "mercado": {
                "id": par_mercado,
                "bloco": inf_mkt["name_bloc"],
                "desc_b": inf_mkt["desc_bloc"],
                "derv": inf_mkt["name_derv"],
                "desc_d": inf_mkt["desc_derv"],
            },
        },
        "scores_dominios": scores_dominios_json,
    }

    cur.execute(
        """
        INSERT INTO ctdi_matu_presurvey (
            id_matu,
            score_estrat_p, score_estrat_f,
            score_organiz_p, score_organiz_f,
            score_humana_p, score_humana_f,
            score_pedag_p, score_pedag_f,
            score_tecno_p, score_tecno_f,
            json_insights
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_matu) DO UPDATE SET
            score_estrat_p = EXCLUDED.score_estrat_p,
            score_estrat_f = EXCLUDED.score_estrat_f,
            score_organiz_p = EXCLUDED.score_organiz_p,
            score_organiz_f = EXCLUDED.score_organiz_f,
            score_humana_p = EXCLUDED.score_humana_p,
            score_humana_f = EXCLUDED.score_humana_f,
            score_pedag_p = EXCLUDED.score_pedag_p,
            score_pedag_f = EXCLUDED.score_pedag_f,
            score_tecno_p = EXCLUDED.score_tecno_p,
            score_tecno_f = EXCLUDED.score_tecno_f,
            json_insights = EXCLUDED.json_insights,
            data_criacao = CURRENT_TIMESTAMP
        """,
        (
            id_matu,
            _media(stats_dime[1]["P"]),
            _media(stats_dime[1]["F"]),
            _media(stats_dime[3]["P"]),
            _media(stats_dime[3]["F"]),
            _media(stats_dime[2]["P"]),
            _media(stats_dime[2]["F"]),
            _media(stats_dime[4]["P"]),
            _media(stats_dime[4]["F"]),
            _media(stats_dime[5]["P"]),
            _media(stats_dime[5]["F"]),
            json.dumps(insights_data),
        ),
    )
    cur.execute(
        "UPDATE ctdi_matu SET status_ia = 'PRESURVEY OK' WHERE id_matu = %s",
        (id_matu,),
    )


def filter_education_answers(all_answers: list[dict]) -> list[dict]:
    subset = []
    for ans in all_answers:
        try:
            dime = int(ans.get("id_dime", 0))
        except (TypeError, ValueError):
            dime = 0
        setor = str(ans.get("setor_ques", "")).strip().upper()
        if dime == 4 or setor == "EDUCACAO":
            subset.append(ans)
    return subset


def calculate_scores(answers_list: list[dict]):
    respostas_por_dominio: dict[int, list[float]] = {}
    respostas_por_dimensao: dict[int, list[float]] = {}

    for answer in answers_list:
        grad = answer.get("grad_ques")
        if grad is None or not isinstance(grad, (int, float)):
            continue
        respostas_por_dominio.setdefault(answer["id_doma"], []).append(float(grad))
        respostas_por_dimensao.setdefault(answer["id_dime"], []).append(float(grad))

    pdom_scores = {
        str(d): round(sum(scores) / len(scores), 2)
        for d, scores in respostas_por_dominio.items()
        if scores
    }
    pdim_scores = {
        str(d): round(sum(scores) / len(scores), 2)
        for d, scores in respostas_por_dimensao.items()
        if scores
    }

    pdom_avg = sum(pdom_scores.values()) / len(pdom_scores) if pdom_scores else 0.0
    pdim_avg = sum(pdim_scores.values()) / len(pdim_scores) if pdim_scores else 0.0
    pgen = round((pdom_avg + pdim_avg) / 2, 2) if (pdom_avg + pdim_avg) > 0 else 0.0
    return pdom_scores, pdim_scores, pgen


def finalize_full_assessment(cur, id_matu: int) -> None:
    """Replica finalize=true de POST /api/ctdi_surv."""
    cur.execute(
        """
        SELECT s.id_ques, s.grad_ques, s.id_dime, s.id_doma, q.prefu_ques, q.setor_ques
        FROM ctdi_surv s
        JOIN ctdi_quest q ON s.id_ques = q.id_ques
        WHERE s.id_matu = %s
        """,
        (id_matu,),
    )
    answers = list(cur.fetchall())
    pres = [a for a in answers if (a.get("prefu_ques") or "").upper() == "P"]
    fut = [a for a in answers if (a.get("prefu_ques") or "").upper() == "F"]
    if not pres or not fut:
        raise RuntimeError(
            "Avaliação completa exige respostas Presente (P) e Futuro (F). "
            "Verifique o catálogo ctdi_quest."
        )

    pdom_pres, pdim_pres, pgen_pres = calculate_scores(pres)
    pdom_fut, pdim_fut, pgen_fut = calculate_scores(fut)

    pdom_gap = {k: round(pdom_fut.get(k, 0.0) - pdom_pres.get(k, 0.0), 2) for k in pdom_fut}
    pdim_gap = {k: round(pdim_fut.get(k, 0.0) - pdim_pres.get(k, 0.0), 2) for k in pdim_fut}
    pgen_gap = round(pgen_fut - pgen_pres, 2)

    sect = filter_education_answers(answers)
    sect_pres = [a for a in sect if (a.get("prefu_ques") or "").upper() == "P"]
    sect_fut = [a for a in sect if (a.get("prefu_ques") or "").upper() == "F"]

    if sect_pres and sect_fut:
        pdom_sect_pres, pdim_sect_pres, pgen_sect_pres = calculate_scores(sect_pres)
        pdom_sect_fut, pdim_sect_fut, pgen_sect_fut = calculate_scores(sect_fut)
        pdom_sect_gap = {
            k: round(pdom_sect_fut.get(k, 0.0) - pdom_sect_pres.get(k, 0.0), 2)
            for k in pdom_sect_fut
        }
        pdim_sect_gap = {
            k: round(pdim_sect_fut.get(k, 0.0) - pdim_sect_pres.get(k, 0.0), 2)
            for k in pdim_sect_fut
        }
        pgen_sect_gap = round(pgen_sect_fut - pgen_sect_pres, 2)
    else:
        pdom_sect_pres = pdom_sect_fut = pdom_sect_gap = {}
        pdim_sect_pres = pdim_sect_fut = pdim_sect_gap = {}
        pgen_sect_pres = pgen_sect_fut = pgen_sect_gap = 0.0

    cur.execute(
        """
        UPDATE ctdi_matu SET
            pdom_pres = %s, pdim_pres = %s, pgen_pres = %s,
            pdom_fut = %s, pdim_fut = %s, pgen_fut = %s,
            pdom_gap = %s, pdim_gap = %s, pgen_gap = %s,
            pdom_sect_pres = %s, pdim_sect_pres = %s, pgen_sect_pres = %s,
            pdom_sect_fut = %s, pdim_sect_fut = %s, pgen_sect_fut = %s,
            pdom_sect_gap = %s, pdim_sect_gap = %s, pgen_sect_gap = %s,
            status_ia = 'AVALIACAO OK',
            txt_diagnostico_ia = 'Aguardando Ativação (ActionHub)',
            dt_fim_ia = NOW()
        WHERE id_matu = %s
        """,
        (
            Json(pdom_pres),
            Json(pdim_pres),
            pgen_pres,
            Json(pdom_fut),
            Json(pdim_fut),
            pgen_fut,
            Json(pdom_gap),
            Json(pdim_gap),
            pgen_gap,
            Json(pdom_sect_pres),
            Json(pdim_sect_pres),
            pgen_sect_pres,
            Json(pdom_sect_fut),
            Json(pdim_sect_fut),
            pgen_sect_fut,
            Json(pdom_sect_gap),
            Json(pdim_sect_gap),
            pgen_sect_gap,
            id_matu,
        ),
    )


def _import_sprint_squad():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from sprint_squad import (  # noqa: WPS433
        atualizar_nome_squad_pos_sprint,
        criar_squad_vazia_para_sprint,
        resolver_ou_criar_projeto_cliente,
    )

    return (
        criar_squad_vazia_para_sprint,
        atualizar_nome_squad_pos_sprint,
        resolver_ou_criar_projeto_cliente,
    )


def repair_sprint_squads_for_client(cur, id_clie: int) -> int:
    """Garante 1 squad vazia por sprint sem id_squad (Regra 4 — governança LeAction)."""
    (
        criar_squad_vazia_para_sprint,
        atualizar_nome_squad_pos_sprint,
        resolver_ou_criar_projeto_cliente,
    ) = _import_sprint_squad()

    id_proj = resolver_ou_criar_projeto_cliente(cur, id_clie)
    cur.execute(
        """
        SELECT s.id_sprn, s.name_sprn
        FROM public.ctdi_sprn s
        JOIN public.ctdi_itera i ON i.id_itera = s.id_itera
        JOIN public.ctdi_main m ON m.id_ctdi = i.id_ctdi
        JOIN public.ctdi_matu ma ON ma.id_matu = m.id_matu
        WHERE ma.id_clie = %s AND s.id_squad IS NULL
        ORDER BY s.ordr_sprn NULLS LAST, s.id_sprn
        """,
        (id_clie,),
    )
    rows = cur.fetchall()
    for row in rows:
        id_sprn = row["id_sprn"]
        nome_sprn = row["name_sprn"]
        id_squad = criar_squad_vazia_para_sprint(
            cur, id_proj=id_proj, nome_sprint=nome_sprn
        )
        cur.execute(
            "UPDATE public.ctdi_sprn SET id_squad = %s WHERE id_sprn = %s;",
            (id_squad, id_sprn),
        )
        atualizar_nome_squad_pos_sprint(cur, id_squad, nome_sprn, id_sprn)
    return len(rows)


def seed_mock_plan_and_kanban(cur, id_clie: int, id_matu: int) -> None:
    """Estágio 4 — plano geral + Kanban sem chamar Bedrock."""
    cur.execute(
        """
        UPDATE ctdi_clie SET
            has_active_project = true,
            tipo_ensino = 'K12',
            qtd_alunos = 620,
            qtd_colaboradores = 48,
            clima_organizacional = 'Equipe receptiva à transformação digital',
            dados_mercado = 'Mercado educacional competitivo na região metropolitana.',
            dados_etnograficos = 'Comunidade escolar engajada em eventos pedagógicos.'
        WHERE id_clie = %s
        """,
        (id_clie,),
    )

    cur.execute(
        """
        INSERT INTO ctdi_main (id_matu, id_dime, name_ctdi, stat_ctdi)
        VALUES (%s, 1, 'Plano de Aceleração Digital', 'ativo')
        RETURNING id_ctdi
        """,
        (id_matu,),
    )
    id_ctdi = cur.fetchone()["id_ctdi"]

    cur.execute(
        """
        INSERT INTO ctdi_projetos (id_clie, id_ctdi, status, fase_atual, data_geracao_plano)
        VALUES (%s, %s, 'ATIVO', 'Plano Estratégico Disponível (Onda 1)', NOW())
        ON CONFLICT (id_clie) DO UPDATE SET
            id_ctdi = EXCLUDED.id_ctdi,
            status = 'ATIVO',
            fase_atual = EXCLUDED.fase_atual,
            data_geracao_plano = NOW()
        RETURNING id_proj
        """,
        (id_clie, id_ctdi),
    )
    id_proj = int(cur.fetchone()["id_proj"])

    (
        criar_squad_vazia_para_sprint,
        atualizar_nome_squad_pos_sprint,
        _resolver_proj,
    ) = _import_sprint_squad()
    id_proj = _resolver_proj(cur, id_clie) or id_proj

    cur.execute(
        """
        INSERT INTO ctdi_itera (id_ctdi, id_phase, name_itera, stat_itera)
        VALUES (%s, 1, 'Onda 1 — Core Roadmap', 'ativa')
        RETURNING id_itera
        """,
        (id_ctdi,),
    )
    id_itera = cur.fetchone()["id_itera"]

    cur.execute(
        """
        SELECT id_bloc, name_bloc
        FROM leaf_bloc
        ORDER BY id_bloc
        LIMIT 5
        """
    )
    blocos = cur.fetchall()
    if not blocos:
        raise RuntimeError("leaf_bloc vazio — impossível criar sprints de demonstração.")

    plano_json = {
        "roadmap_estrategico": [
            {
                "nome_sprint": blocos[i % len(blocos)]["name_bloc"],
                "id_bloco": blocos[i % len(blocos)]["id_bloc"],
                "justificativa": "Prioridade simulada pelo seed de desenvolvimento.",
            }
            for i in range(min(4, len(blocos)))
        ]
    }

    for ordem, bloco in enumerate(blocos[:4], start=1):
        nome_sprn = f"[DEV] {bloco['name_bloc']}"
        stat_sprn = "ativa" if ordem == 1 else "planejada"
        id_squad = criar_squad_vazia_para_sprint(
            cur, id_proj=id_proj, nome_sprint=nome_sprn
        )
        cur.execute(
            """
            INSERT INTO ctdi_sprn (
                id_bloc, id_itera, id_squad, name_sprn, desc_sprn, stat_sprn, ordr_sprn
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_sprn
            """,
            (
                bloco["id_bloc"],
                id_itera,
                id_squad,
                nome_sprn,
                "Sprint gerada pelo seed_dev_client.py (mock).",
                stat_sprn,
                ordem,
            ),
        )
        id_sprn = int(cur.fetchone()["id_sprn"])
        atualizar_nome_squad_pos_sprint(cur, id_squad, nome_sprn, id_sprn)

    cur.execute(
        """
        UPDATE ctdi_matu SET
            status_ia = 'CONCLUIDO',
            json_plano_estrategico = %s,
            txt_diagnostico_ia = 'Plano estratégico simulado para desenvolvimento local.',
            dt_fim_ia = NOW()
        WHERE id_matu = %s
        """,
        (Json(plano_json), id_matu),
    )


def apply_stage(cur, stage: int, id_clie: int, id_matu: int) -> str:
    if stage == 1:
        return "AGUARDANDO CONTEXTO"

    if stage >= 2:
        n = insert_random_survey_answers(cur, id_matu, presurvey_only=True)
        run_presurvey_calculation(cur, id_matu)
        print(f"    -> {n} respostas de pre-survey (aleatorias)")

    if stage == 2:
        return "PRESURVEY OK"

    if stage >= 3:
        n = insert_random_survey_answers(cur, id_matu, presurvey_only=False)
        finalize_full_assessment(cur, id_matu)
        print(f"    -> {n} respostas do questionario completo (aleatorias)")

    if stage == 3:
        return "AVALIACAO OK"

    seed_mock_plan_and_kanban(cur, id_clie, id_matu)
    n_repair = repair_sprint_squads_for_client(cur, id_clie)
    if n_repair:
        print(f"    -> {n_repair} sprint(s) reparada(s) com squad vazia")
    return "CONCLUIDO"


def print_summary(id_clie: int, id_matu: int, status: str, stage: int, *, lead_only: bool = False) -> None:
    sys_p, exe_p = get_team_passwords()
    print("\n" + "=" * 60)
    print("SEED CONCLUÍDO")
    print("=" * 60)
    print(f"  Estágio solicitado : {stage}")
    print(f"  Lead (código)        : {DEV_EMAIL} / {DEV_ACCESS_CODE}")
    if not lead_only:
        print(f"  Sysadmin (senha)     : {SYSADMIN_EMAIL} / {sys_p}")
        print(f"  Executor (senha)     : {EXECUTOR_EMAIL} / {exe_p}")
    print(f"  id_clie              : {id_clie}")
    print(f"  id_matu              : {id_matu}")
    print(f"  status_ia            : {status}")
    print("-" * 60)
    stages = {
        1: "Primeiro login (Insight Gate / sem assessment)",
        2: "Pós avaliação inicial (relatório provisório)",
        3: "Pós avaliação completa (matriz / Gênese)",
        4: "Pós plano geral (Kanban + Panorama)",
    }
    print(f"  Cenário              : {stages.get(stage, '—')}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reseta a base local e cria cliente dev sistema@paneldx.com.br"
    )
    parser.add_argument(
        "stage",
        type=int,
        choices=[1, 2, 3, 4],
        help="1=login | 2=pré-survey | 3=avaliação completa | 4=plano gerado",
    )
    parser.add_argument(
        "--full-reset",
        action="store_true",
        help="TRUNCATE em toda a base (somente recomendado em dev local)",
    )
    parser.add_argument(
        "--lead-only",
        action="store_true",
        help="Remove e recria SOMENTE sistema@paneldx.com.br (sem sysadmin/executor)",
    )
    args = parser.parse_args()

    cfg = get_db_config()
    env_kind = assert_environment(cfg, lead_only=args.lead_only)
    if args.full_reset and env_kind != "local":
        raise SystemExit("Abortado: --full-reset so e permitido com DB_HOST local.")
    if args.lead_only and args.full_reset:
        raise SystemExit("Abortado: --lead-only nao pode ser usado com --full-reset.")

    conn = connect_db(cfg)
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if args.full_reset:
                reset_database_full(cur)
            elif args.lead_only:
                reset_lead_only(cur)
            else:
                reset_demo_accounts(cur)
            if not args.lead_only:
                seed_team_accounts(cur)
            id_clie, id_matu = create_dev_client(cur)
            sync_paneldx_usuarios(cur, id_clie)
            status = apply_stage(cur, args.stage, id_clie, id_matu)
        conn.commit()
        print_summary(id_clie, id_matu, status, args.stage, lead_only=args.lead_only)
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"\nErro: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
