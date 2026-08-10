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
_nina_onboarding_ensured = False

# Freemium Starter (solo): 1 desafio IA. Dia a Dia: só navegação (registro=0).
CREDITO_IA_FREEMIUM_DEFAULT = 1
PLAN_TIER_STARTER = "starter"
PLAN_TIER_PRO = "profissional"
PLAN_TIER_MENTOR = "mentor"
FREEMIUM_AULAS_MES = 0


def ensure_creditos_ia_column() -> None:
    """Garante coluna freemium creditos_ia + plan_tier em ctdi_clie."""
    global _creditos_ensured
    if _creditos_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS creditos_ia INTEGER NOT NULL
                    DEFAULT {int(CREDITO_IA_FREEMIUM_DEFAULT)};
                """
            )
            cur.execute(
                f"""
                ALTER TABLE public.ctdi_clie
                    ALTER COLUMN creditos_ia
                    SET DEFAULT {int(CREDITO_IA_FREEMIUM_DEFAULT)};
                """
            )
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(32) NOT NULL DEFAULT 'starter'
                """
            )
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            cur.execute(
                """
                UPDATE public.ctdi_clie
                SET is_test = TRUE
                WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br'
                  AND COALESCE(is_test, FALSE) = FALSE
                """
            )
    _creditos_ensured = True
    ensure_nina_onboarding_column()
    ensure_instituicao_b2b_columns()


def ensure_nina_onboarding_column() -> None:
    """Garante coluna nina_onboarding_done em ctdi_clie."""
    global _nina_onboarding_ensured
    if _nina_onboarding_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS nina_onboarding_done
                    BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
    _nina_onboarding_ensured = True


_instituicao_b2b_ensured = False


def ensure_instituicao_b2b_columns() -> None:
    """Garante instituicao_b2b_id + institutional_name em ctdi_clie (Chave Mestra)."""
    global _instituicao_b2b_ensured
    if _instituicao_b2b_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS instituicao_b2b_id UUID
                """
            )
            cur.execute(
                """
                ALTER TABLE public.ctdi_clie
                    ADD COLUMN IF NOT EXISTS institutional_name TEXT
                """
            )
    _instituicao_b2b_ensured = True


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
                       init_role, has_active_project, creditos_ia, plan_tier,
                       COALESCE(nina_onboarding_done, FALSE) AS nina_onboarding_done,
                       instituicao_b2b_id,
                       institutional_name
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
    """Grava lead freemium em ctdi_clie (+ slot ctdi_matu). Novos leads: 1 crédito IA."""
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
                    has_active_project, justificativa_solo, creditos_ia, plan_tier,
                    nina_onboarding_done
                )
                VALUES (%s, %s, %s, 'GENERAL', false, %s, %s, 'starter', FALSE)
                RETURNING id_clie, nome_clie, mail_clie, empresa_clie,
                          init_role, has_active_project, creditos_ia, plan_tier,
                          COALESCE(nina_onboarding_done, FALSE) AS nina_onboarding_done
                """,
                (
                    nome,
                    email,
                    empresa,
                    "Lead freemium inove4us — Mesa do Inovador",
                    int(CREDITO_IA_FREEMIUM_DEFAULT),
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


def set_nina_onboarding_done(id_clie: int, done: bool = True) -> bool:
    """Marca (ou limpa) a conclusão do onboarding da Nina."""
    ensure_nina_onboarding_column()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.ctdi_clie
                   SET nina_onboarding_done = %s
                 WHERE id_clie = %s
                """,
                (bool(done), int(id_clie)),
            )
            return cur.rowcount > 0


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


def get_plan_tier(id_clie: int) -> str:
    ensure_creditos_ia_column()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(plan_tier, 'starter') FROM public.ctdi_clie WHERE id_clie = %s",
                (int(id_clie),),
            )
            row = cur.fetchone()
            if not row:
                return PLAN_TIER_STARTER
            tier = str(row[0] or PLAN_TIER_STARTER).strip().lower()
            if tier in (PLAN_TIER_PRO, PLAN_TIER_MENTOR):
                return tier
            return PLAN_TIER_STARTER


def set_plan_tier(id_clie: int, tier: str) -> str:
    """Atualiza plan_tier (profissional|mentor|starter)."""
    ensure_creditos_ia_column()
    normalized = str(tier or PLAN_TIER_STARTER).strip().lower()
    if normalized not in (PLAN_TIER_STARTER, PLAN_TIER_PRO, PLAN_TIER_MENTOR):
        normalized = PLAN_TIER_STARTER
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.ctdi_clie
                   SET plan_tier = %s
                 WHERE id_clie = %s
             RETURNING plan_tier
                """,
                (normalized, int(id_clie)),
            )
            row = cur.fetchone()
            return str(row[0]) if row else normalized


def count_aulas_simples_mes(id_clie: int) -> int:
    """Conta aulas simples criadas no mês civil atual (por created_at)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int
                  FROM public.inove_aulas_simples
                 WHERE id_clie = %s
                   AND date_trunc('month', COALESCE(created_at, CURRENT_TIMESTAMP))
                       = date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0


def is_institutional_cliente(id_clie: int) -> bool:
    """True se o inovador está vinculado a uma escola (Chave Mestra B2B)."""
    ensure_instituicao_b2b_columns()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT instituicao_b2b_id
                  FROM public.ctdi_clie
                 WHERE id_clie = %s
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
            return bool(row and row[0])


def aulas_simples_quota(id_clie: int) -> dict:
    """
    Limite de registro no Dia a Dia.
    Solo freemium (starter): bloqueado (só navegação).
    Profissional / Mentor / institucional: ilimitado.
    """
    tier = get_plan_tier(id_clie)
    usados = count_aulas_simples_mes(id_clie)
    if tier in (PLAN_TIER_PRO, PLAN_TIER_MENTOR) or is_institutional_cliente(id_clie):
        return {
            "tier": tier,
            "limite": None,
            "usados": usados,
            "restantes": None,
            "ilimitado": True,
            "bloqueado": False,
        }
    restantes = max(0, int(FREEMIUM_AULAS_MES) - usados)
    return {
        "tier": tier,
        "limite": int(FREEMIUM_AULAS_MES),
        "usados": usados,
        "restantes": restantes,
        "ilimitado": False,
        "bloqueado": restantes <= 0,
    }


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


_hub_notices_ensured = False


def ensure_hub_notices_table() -> None:
    """Avisos do Action Hub (pagamento pendente / intervenção admin)."""
    global _hub_notices_ensured
    if _hub_notices_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.hub_notices (
                    id SERIAL PRIMARY KEY,
                    mail_clie TEXT NOT NULL,
                    order_id TEXT,
                    message TEXT NOT NULL,
                    status_label TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    dismissed_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hub_notices_mail_active
                    ON public.hub_notices (LOWER(TRIM(mail_clie)))
                    WHERE dismissed_at IS NULL
                """
            )
    _hub_notices_ensured = True


def upsert_hub_notice(
    *,
    mail_clie: str,
    message: str,
    order_id: str | None = None,
    status_label: str | None = None,
) -> dict:
    ensure_hub_notices_table()
    mail = (mail_clie or "").strip().lower()
    text = (message or "").strip()
    if not mail or not text:
        raise ValueError("mail_clie e message são obrigatórios")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Substitui aviso ativo do mesmo pedido (se houver)
            if order_id:
                cur.execute(
                    """
                    UPDATE public.hub_notices
                    SET dismissed_at = CURRENT_TIMESTAMP
                    WHERE LOWER(TRIM(mail_clie)) = %s
                      AND order_id = %s
                      AND dismissed_at IS NULL
                    """,
                    (mail, str(order_id)),
                )
            cur.execute(
                """
                INSERT INTO public.hub_notices (mail_clie, order_id, message, status_label)
                VALUES (%s, %s, %s, %s)
                RETURNING id, mail_clie, order_id, message, status_label, created_at
                """,
                (mail, order_id, text, status_label),
            )
            return dict(cur.fetchone())


def list_active_hub_notices(mail_clie: str, limit: int = 5) -> list[dict]:
    ensure_hub_notices_table()
    mail = (mail_clie or "").strip().lower()
    if not mail:
        return []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, order_id, message, status_label, created_at
                FROM public.hub_notices
                WHERE LOWER(TRIM(mail_clie)) = %s
                  AND dismissed_at IS NULL
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (mail, max(1, min(20, int(limit)))),
            )
            return [dict(r) for r in cur.fetchall()]


def dismiss_hub_notice(mail_clie: str, notice_id: int) -> bool:
    ensure_hub_notices_table()
    mail = (mail_clie or "").strip().lower()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.hub_notices
                SET dismissed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND LOWER(TRIM(mail_clie)) = %s
                  AND dismissed_at IS NULL
                """,
                (int(notice_id), mail),
            )
            return cur.rowcount > 0


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
                       c.init_role, c.has_active_project, c.creditos_ia, c.plan_tier,
                       COALESCE(c.nina_onboarding_done, FALSE) AS nina_onboarding_done,
                       a.access_code
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
