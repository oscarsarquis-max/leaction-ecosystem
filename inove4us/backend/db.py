"""Conexão PostgreSQL — DB inove4us (solicitações em ctdi_clie)."""

from __future__ import annotations

import os
import random
import string
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


def get_dsn() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT", "5433")),
        "dbname": os.environ.get("DB_NAME", "inove4us"),
        "user": os.environ.get("DB_USER", "admin"),
        "password": os.environ.get("DB_PASS", ""),
        "sslmode": os.environ.get("DB_SSLMODE", "disable"),
    }


@contextmanager
def get_conn():
    conn = psycopg2.connect(**get_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_creditos_ensured = False


def ensure_creditos_ia_column() -> None:
    """Garante coluna freemium creditos_ia em ctdi_clie (default 10)."""
    global _creditos_ensured
    if _creditos_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS creditos_ia INTEGER NOT NULL DEFAULT 10;
                """
            )
    _creditos_ensured = True


def find_cliente_by_email(email: str) -> dict | None:
    """Consulta solicitações (ctdi_clie) pelo e-mail — case-insensitive."""
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, nome_clie, mail_clie, empresa_clie,
                       init_role, has_active_project, creditos_ia
                FROM public.ctdi_clie
                WHERE mail_clie IS NOT NULL
                  AND LOWER(TRIM(mail_clie)) = %s
                ORDER BY id_clie DESC
                LIMIT 1
                """,
                (normalized,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def create_lead_solicitacao(*, nome: str, email: str, empresa: str) -> dict:
    """Grava lead freemium em ctdi_clie (+ slot ctdi_matu). Novos leads: 10 créditos IA."""
    nome = (nome or "").strip()
    email = (email or "").strip().lower()
    empresa = (empresa or "").strip() or None
    if not nome or not email:
        raise ValueError("Nome e e-mail são obrigatórios.")

    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.ctdi_clie (
                    nome_clie, mail_clie, empresa_clie, init_role,
                    has_active_project, justificativa_solo, creditos_ia
                )
                VALUES (%s, %s, %s, 'GENERAL', false, %s, 10)
                RETURNING id_clie, nome_clie, mail_clie, empresa_clie,
                          init_role, has_active_project, creditos_ia
                """,
                (
                    nome,
                    email,
                    empresa,
                    "Lead freemium inove4us — Mesa do Inovador",
                ),
            )
            cliente = dict(cur.fetchone())

            cur.execute(
                """
                INSERT INTO public.ctdi_matu (id_clie, status_ia)
                VALUES (%s, 'SANDBOX')
                RETURNING id_matu
                """,
                (cliente["id_clie"],),
            )
            matu = cur.fetchone()
            cliente["id_matu"] = matu["id_matu"] if matu else None
            return cliente


def get_creditos_ia(id_clie: int) -> int:
    """Saldo atual de créditos de geração de plano (IA)."""
    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT creditos_ia FROM public.ctdi_clie WHERE id_clie = %s",
                (int(id_clie),),
            )
            row = cur.fetchone()
            if not row:
                return 0
            return int(row[0] or 0)


def consumir_credito_ia(id_clie: int) -> int | None:
    """
    Decrementa 1 crédito se houver saldo.
    Retorna o novo saldo, ou None se não havia crédito / cliente inexistente.
    """
    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.ctdi_clie
                SET creditos_ia = creditos_ia - 1
                WHERE id_clie = %s AND creditos_ia > 0
                RETURNING creditos_ia
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return int(row[0])


def adicionar_creditos_ia(id_clie: int, quantidade: int) -> int:
    """
    Soma créditos IA (webhook Action Hub / pacotes).
    Retorna o novo saldo.
    """
    ensure_creditos_ia_column()
    delta = max(0, int(quantidade or 0))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.ctdi_clie
                SET creditos_ia = creditos_ia + %s
                WHERE id_clie = %s
                RETURNING creditos_ia
                """,
                (delta, int(id_clie)),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Cliente id_clie={id_clie} não encontrado")
            return int(row[0])

def gerar_codigo_acesso() -> str:
    sufixo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"LA-{sufixo}"


def upsert_access_code(id_clie: int, access_code: str | None = None) -> str:
    """Cria ou atualiza código em ctdi_lead_access (1 por cliente)."""
    code = (access_code or gerar_codigo_acesso()).strip().upper()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.ctdi_lead_access (id_clie, access_code)
                VALUES (%s, %s)
                ON CONFLICT (id_clie) DO UPDATE
                  SET access_code = EXCLUDED.access_code,
                      created_at = now()
                """,
                (id_clie, code),
            )
    return code


def verify_access_code(email: str, code: str) -> dict | None:
    """Valida e-mail + código (aceita LA-XXXXXX ou só o sufixo)."""
    email_n = (email or "").strip().lower()
    provided = (code or "").strip().upper()
    if not email_n or not provided:
        return None
    provided_core = provided[3:] if provided.startswith("LA-") else provided

    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT c.id_clie, c.nome_clie, c.mail_clie, c.empresa_clie,
                       c.init_role, c.has_active_project, c.creditos_ia, a.access_code
                FROM public.ctdi_clie c
                JOIN public.ctdi_lead_access a ON a.id_clie = c.id_clie
                WHERE LOWER(TRIM(c.mail_clie)) = %s
                LIMIT 1
                """,
                (email_n,),
            )
            row = cur.fetchone()
            if not row:
                return None
            stored = (row.get("access_code") or "").strip().upper()
            stored_core = stored[3:] if stored.startswith("LA-") else stored
            if stored != provided and stored_core != provided_core:
                return None
            return dict(row)
