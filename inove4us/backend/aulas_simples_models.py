"""Contrato do vetor Dia a Dia (AulaSimples). Sem ORM — DDL via migration + ensure_*."""

from __future__ import annotations

from typing import Literal, TypedDict

AulaSimplesStatus = Literal["draft", "planejado", "realizado"]
DinamicaFonte = Literal["mativas", "inove_local", "livre"]

STATUSES: frozenset[str] = frozenset({"draft", "planejado", "realizado"})
FONTES: frozenset[str] = frozenset({"mativas", "inove_local", "livre"})

_ensured = False


class AulaSimplesRow(TypedDict, total=False):
    id: int
    id_clie: int
    data_planejada: str
    turma_nome: str | None
    tema_aula: str
    objetivo_aprendizagem: str
    acolhida: str
    conteudo_essencial: str
    dinamica_ativa_id: str | None
    dinamica_ativa_fonte: DinamicaFonte
    fechamento_checkout: str
    status: AulaSimplesStatus
    id_evento_agenda: int | None
    created_at: str
    updated_at: str


def ensure_aulas_simples_table(conn) -> None:
    """
    Idempotente — espelha o padrão de inove_user_feedbacks.

    ATENÇÃO: em produção, preferir aplicar 007_inove_aulas_simples.sql
    explicitamente após o cutover financeiro. Este ensure existe para
    ambientes locais / pós-liberação do vetor Dia a Dia.
    """
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_aulas_simples (
                id                    BIGSERIAL PRIMARY KEY,
                id_clie               INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                data_planejada        DATE NOT NULL,
                turma_nome            VARCHAR(120),
                tema_aula             VARCHAR(255) NOT NULL,
                objetivo_aprendizagem TEXT NOT NULL DEFAULT '',
                acolhida              TEXT NOT NULL DEFAULT '',
                conteudo_essencial    TEXT NOT NULL DEFAULT '',
                dinamica_ativa_id     VARCHAR(160),
                dinamica_ativa_fonte  VARCHAR(32) NOT NULL DEFAULT 'mativas',
                fechamento_checkout   TEXT NOT NULL DEFAULT '',
                status                VARCHAR(32) NOT NULL DEFAULT 'draft',
                id_evento_agenda      INTEGER,
                kanban_state          JSONB,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_inove_aulas_simples_status
                    CHECK (status IN ('draft', 'planejado', 'realizado')),
                CONSTRAINT chk_inove_aulas_simples_fonte
                    CHECK (dinamica_ativa_fonte IN ('mativas', 'inove_local', 'livre'))
            );
            ALTER TABLE public.inove_aulas_simples
                ADD COLUMN IF NOT EXISTS id_evento_agenda INTEGER;
            ALTER TABLE public.inove_aulas_simples
                ADD COLUMN IF NOT EXISTS kanban_state JSONB;
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_clie_data
                ON public.inove_aulas_simples (id_clie, data_planejada DESC);
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_status
                ON public.inove_aulas_simples (status, data_planejada DESC);
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_dinamica
                ON public.inove_aulas_simples (dinamica_ativa_id)
                WHERE dinamica_ativa_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_evento
                ON public.inove_aulas_simples (id_evento_agenda)
                WHERE id_evento_agenda IS NOT NULL;
            """
        )
    _ensured = True


def list_aulas_by_clie(conn, id_clie: int, *, limit: int = 100) -> list[dict]:
    """Backref lógico: ctdi_clie (1) —< (N) inove_aulas_simples."""
    ensure_aulas_simples_table(conn)
    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT *
              FROM public.inove_aulas_simples
             WHERE id_clie = %s
             ORDER BY data_planejada DESC, id DESC
             LIMIT %s
            """,
            (int(id_clie), max(1, min(int(limit), 200))),
        )
        return [dict(r) for r in cur.fetchall()]
