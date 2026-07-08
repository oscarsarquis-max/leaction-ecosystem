"""Estados da jornada do cliente — espelho PanelDX status_ia (ctdi_matu)."""

from __future__ import annotations

# Funnel principal
JOURNEY_AGUARDANDO_CONTEXTO = "AGUARDANDO CONTEXTO"
JOURNEY_PRESURVEY_OK = "PRESURVEY OK"
JOURNEY_PROJETO_OK = "PROJETO OK"
JOURNEY_CONTEXTO_OK = "CONTEXTO OK"
JOURNEY_AVALIACAO_OK = "AVALIACAO OK"
JOURNEY_PENDENTE = "PENDENTE"
JOURNEY_PROCESSANDO = "PROCESSANDO"
JOURNEY_CONCLUIDO = "CONCLUIDO"
JOURNEY_ERRO_IA = "ERRO_IA"

JOURNEY_DEFAULT = JOURNEY_AGUARDANDO_CONTEXTO

# Kanban / Gênese (PanelDX sprint_governance.py)
GENESE_KANBAN_MAX = 12
GENESE_ONDA1_ATIVAS = 3

KANBAN_STAT_EM_ANALISE = "em_analise"
KANBAN_STAT_PLANEJADA = "planejada_backlog"
KANBAN_STAT_ANDAMENTO = "em_andamento"
KANBAN_STAT_CONCLUIDA = "concluida"

KANBAN_COLUMNS = (
    {"id": KANBAN_STAT_EM_ANALISE, "label": "Inovação (Em Análise)"},
    {"id": KANBAN_STAT_PLANEJADA, "label": "Planejada (Backlog)"},
    {"id": KANBAN_STAT_ANDAMENTO, "label": "Em Andamento"},
    {"id": KANBAN_STAT_CONCLUIDA, "label": "Concluído"},
)
