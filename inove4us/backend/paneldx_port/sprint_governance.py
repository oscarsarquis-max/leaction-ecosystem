"""Governança de status de Sprints no Kanban — Framework LeAction."""

from __future__ import annotations

# Status canônicos (ctdi_sprn.stat_sprn)
STAT_EM_ANALISE = "em_analise"
STAT_PLANEJADA_BACKLOG = "planejada_backlog"
STAT_EM_ANDAMENTO = "em_andamento"
STAT_CONCLUIDA = "concluida"

# Gênese IA Master
GENESE_KANBAN_MAX = 12
GENESE_ONDA1_ATIVAS = 3

# Coluna Inovação — origens externas / ad-hoc
ORIGENS_EM_ANALISE = frozenset({
    "mesa de inovação - paneldx",
    "telemetria base mobile - paneldx",
    "consultor leaction - paneldx",
    "consultor interno - paneldx",
})

_STATUS_DND_CANONICOS = frozenset({
    STAT_PLANEJADA_BACKLOG,
    STAT_EM_ANDAMENTO,
    STAT_CONCLUIDA,
})

_STATUS_DND_ALIASES = {
    "planejada": STAT_PLANEJADA_BACKLOG,
    "planejado": STAT_PLANEJADA_BACKLOG,
    "pendente": STAT_PLANEJADA_BACKLOG,
    "agendada": STAT_PLANEJADA_BACKLOG,
    "agendado": STAT_PLANEJADA_BACKLOG,
    "ativa": STAT_EM_ANDAMENTO,
    "em progresso": STAT_EM_ANDAMENTO,
    "em_progresso": STAT_EM_ANDAMENTO,
    "executando": STAT_EM_ANDAMENTO,
    "concluido": STAT_CONCLUIDA,
    "finalizada": STAT_CONCLUIDA,
}

_COLUNA_EM_ANALISE = frozenset({
    STAT_EM_ANALISE,
    "em analise",
})

_COLUNA_BACKLOG = frozenset({
    STAT_PLANEJADA_BACKLOG,
    "planejada",
    "planejado",
    "pendente",
    "agendada",
    "agendado",
    "",
})

_COLUNA_ANDAMENTO = frozenset({
    STAT_EM_ANDAMENTO,
    "ativa",
    "em progresso",
    "em_progresso",
    "executando",
})

_COLUNA_CONCLUIDA = frozenset({
    STAT_CONCLUIDA,
    "concluido",
    "finalizada",
})


def normalizar_stat(raw: str | None) -> str:
    if raw is None:
        return ""
    return str(raw).lower().strip().replace(" ", "_")


def normalizar_stat_espacos(raw: str | None) -> str:
    if raw is None:
        return ""
    return str(raw).lower().strip()


def canonicalizar_status_dnd(status: str | None) -> str | None:
    if not status:
        return None
    chave = str(status).lower().strip()
    chave_us = chave.replace(" ", "_")
    if chave_us in _STATUS_DND_CANONICOS:
        return chave_us
    if chave in _STATUS_DND_ALIASES:
        return _STATUS_DND_ALIASES[chave]
    if chave_us in _STATUS_DND_ALIASES:
        return _STATUS_DND_ALIASES[chave_us]
    return chave_us


def status_em_analise(raw: str | None) -> bool:
    s = normalizar_stat(raw)
    return s in _COLUNA_EM_ANALISE or normalizar_stat_espacos(raw) in _COLUNA_EM_ANALISE


def status_planejada_backlog(raw: str | None) -> bool:
    s = normalizar_stat(raw)
    esp = normalizar_stat_espacos(raw)
    return s in _COLUNA_BACKLOG or esp in _COLUNA_BACKLOG


def status_em_andamento(raw: str | None) -> bool:
    s = normalizar_stat(raw)
    return s in _COLUNA_ANDAMENTO or normalizar_stat_espacos(raw) in _COLUNA_ANDAMENTO


def status_concluida(raw: str | None) -> bool:
    s = normalizar_stat(raw)
    return s in _COLUNA_CONCLUIDA or normalizar_stat_espacos(raw) in _COLUNA_CONCLUIDA


def status_genese_kanban(indice_zero: int) -> str:
    """Primeiras 3 sprints do plano → em_andamento; demais (até 12) → planejada_backlog."""
    if indice_zero < GENESE_ONDA1_ATIVAS:
        return STAT_EM_ANDAMENTO
    return STAT_PLANEJADA_BACKLOG
