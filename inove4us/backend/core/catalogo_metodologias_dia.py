"""
Catálogo canônico de dinâmicas do vetor Dia a Dia (39 nomes).

Espelha a base da obra usada na MAtivas.
Rótulos de família (substitutos das categorias autorais):
  ÁGEIS      → Agilidade
  ANALÍTICAS → Dedutivas
  IMERSIVAS  → Contextuais
  CRIATIVAS  → Indutivas
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Famílias públicas (nunca usar ÁGEIS / ANALÍTICAS / IMERSIVAS / CRIATIVAS na UI).
ETIQUETA_AGILIDADE = "Agilidade"
ETIQUETA_DEDUTIVAS = "Dedutivas"
ETIQUETA_CONTEXTUAIS = "Contextuais"
ETIQUETA_INDUTIVAS = "Indutivas"

# Remapeamento a partir das categorias autorais / grupos da base.
MAPA_CATEGORIA_PARA_ETIQUETA: dict[str, str] = {
    "ageis": ETIQUETA_AGILIDADE,
    "ágeis": ETIQUETA_AGILIDADE,
    "agil": ETIQUETA_AGILIDADE,
    "ágil": ETIQUETA_AGILIDADE,
    "metodologia agil": ETIQUETA_AGILIDADE,
    "metodologia ágil": ETIQUETA_AGILIDADE,
    "metodologias ageis": ETIQUETA_AGILIDADE,
    "metodologias ágeis": ETIQUETA_AGILIDADE,
    "analiticas": ETIQUETA_DEDUTIVAS,
    "analíticas": ETIQUETA_DEDUTIVAS,
    "analitica": ETIQUETA_DEDUTIVAS,
    "analítica": ETIQUETA_DEDUTIVAS,
    "metodologia analitica": ETIQUETA_DEDUTIVAS,
    "metodologia analítica": ETIQUETA_DEDUTIVAS,
    "metodologias analiticas": ETIQUETA_DEDUTIVAS,
    "metodologias analíticas": ETIQUETA_DEDUTIVAS,
    "imersivas": ETIQUETA_CONTEXTUAIS,
    "imersiva": ETIQUETA_CONTEXTUAIS,
    "metodologia imersiva": ETIQUETA_CONTEXTUAIS,
    "metodologias imersivas": ETIQUETA_CONTEXTUAIS,
    "criativas": ETIQUETA_INDUTIVAS,
    "criativa": ETIQUETA_INDUTIVAS,
    "cri-ativas": ETIQUETA_INDUTIVAS,
    "cri ativas": ETIQUETA_INDUTIVAS,
    "(cri)ativas": ETIQUETA_INDUTIVAS,
    "metodologia (cri)ativa": ETIQUETA_INDUTIVAS,
    "metodologias (cri)ativas": ETIQUETA_INDUTIVAS,
    "metodologias criativas": ETIQUETA_INDUTIVAS,
}


def _norm(texto: str) -> str:
    raw = unicodedata.normalize("NFKD", texto or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(raw.lower().split())


_ETIQUETA_POR_NORM = {
    _norm(ETIQUETA_AGILIDADE): ETIQUETA_AGILIDADE,
    _norm(ETIQUETA_DEDUTIVAS): ETIQUETA_DEDUTIVAS,
    _norm(ETIQUETA_CONTEXTUAIS): ETIQUETA_CONTEXTUAIS,
    _norm(ETIQUETA_INDUTIVAS): ETIQUETA_INDUTIVAS,
}


def etiqueta_publica(categoria_ou_grupo: str | None, fallback: str = ETIQUETA_INDUTIVAS) -> str:
    """Converte categoria/grupo autoral no rótulo público permitido."""
    key = _norm(categoria_ou_grupo or "")
    if not key:
        return fallback
    # Já é um dos quatro rótulos públicos
    if key in _ETIQUETA_POR_NORM:
        return _ETIQUETA_POR_NORM[key]
    if key in MAPA_CATEGORIA_PARA_ETIQUETA:
        return MAPA_CATEGORIA_PARA_ETIQUETA[key]
    # match parcial (ex.: "CRI-ATIVAS", "Metodologias Ágeis")
    for trecho, etiqueta in (
        ("agil", ETIQUETA_AGILIDADE),
        ("analit", ETIQUETA_DEDUTIVAS),
        ("imers", ETIQUETA_CONTEXTUAIS),
        ("cri", ETIQUETA_INDUTIVAS),
    ):
        if trecho in key:
            return etiqueta
    return fallback


def _slug(nome: str) -> str:
    raw = unicodedata.normalize("NFKD", nome or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = raw.lower().strip()
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return raw or "dinamica"


# 39 metodologias — família alinhada a problema_mativa (MAtivas).
# `id_db` (opcional): id em METODOLOGIAS_DB para enriquecer descrição / manter compat.
# `aliases`: nomes/ids alternativos pesquisáveis e resolvíveis.
CATALOGO_METODOLOGIAS_DIA: tuple[dict[str, Any], ...] = (
    # --- Indutivas (ex-CRIATIVAS) ---
    {"nome": "Abordagem Problematizadora", "etiqueta": ETIQUETA_INDUTIVAS},
    {
        "nome": "Aprendizagem Baseada em Casos",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Caso Empático", "criativa_caso_empatico"],
        "id_db": "criativa_caso_empatico",
    },
    {
        "nome": "Aprendizagem Baseada em Equipes",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Team-Based Learning", "TBL"],
    },
    {
        "nome": "Aprendizagem Baseada em Problemas",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["PBL", "ABP", "Aprendizagem Baseada em Problemas (PBL)"],
    },
    {"nome": "Aprendizagem Baseada em Projetos", "etiqueta": ETIQUETA_INDUTIVAS},
    {"nome": "Aprendizagem Maker", "etiqueta": ETIQUETA_INDUTIVAS},
    {"nome": "Coaching Reverso", "etiqueta": ETIQUETA_INDUTIVAS},
    {
        "nome": "Design Thinking",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Design Thinking Express", "DT Express", "ideacao_brainstorming_guiado"],
        "id": "criativa_design_thinking_express",
        "id_db": "criativa_design_thinking_express",
    },
    {"nome": "Mapa de Polaridades", "etiqueta": ETIQUETA_INDUTIVAS},
    {
        "nome": "Narrativas Transmídia em Rotação por Estações",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": [
            "Narrativas Transmídia",
            "Rotação por Estações",
            "criativa_narrativas_transmidia",
            "criativa_rotacao_estacoes",
        ],
        "id": "criativa_narrativas_transmidia",
        "id_db": "criativa_narrativas_transmidia",
    },
    {
        "nome": "Painel da Diversidade de Perspectivas",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Painel de Diversidade", "criativa_painel_diversidade"],
        "id": "criativa_painel_diversidade",
        "id_db": "criativa_painel_diversidade",
    },
    {"nome": "Rotina Veja-Pense-Pergunte-Crie", "etiqueta": ETIQUETA_INDUTIVAS},
    {
        "nome": "Sala de Aula Invertida",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Flipped Classroom"],
    },
    {
        "nome": "World Café",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["World Cafe"],
    },
    # --- Agilidade (ex-ÁGEIS) ---
    {"nome": "Canvas Mania", "etiqueta": ETIQUETA_AGILIDADE},
    {
        "nome": "Discurso de Elevador",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Elevator Pitch", "agil_elevator_pitch"],
        "id": "agil_elevator_pitch",
        "id_db": "agil_elevator_pitch",
    },
    {"nome": "EduScrum", "etiqueta": ETIQUETA_AGILIDADE},
    {
        "nome": "Hackathons",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Hackathon"],
    },
    {
        "nome": "Mapeamento mental",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Mapeamento Mental"],
    },
    {
        "nome": "Minute Paper",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["agil_minute_paper", "rapido_minute_paper"],
        "id": "agil_minute_paper",
        "id_db": "agil_minute_paper",
    },
    {
        "nome": "Pecha Kucha",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["agil_pecha_kucha"],
        "id": "agil_pecha_kucha",
        "id_db": "agil_pecha_kucha",
    },
    {"nome": "Pedagogia Extrema", "etiqueta": ETIQUETA_AGILIDADE},
    # --- Contextuais (ex-IMERSIVAS) ---
    {"nome": "Aprendizagem Baseada em Jogos", "etiqueta": ETIQUETA_CONTEXTUAIS},
    {
        "nome": "Escape Room",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Escape Room Educacional", "imersiva_escape_room"],
        "id": "imersiva_escape_room",
        "id_db": "imersiva_escape_room",
    },
    {
        "nome": "Gamificação de Conteúdo",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["imersiva_gamificacao"],
        "id_db": "imersiva_gamificacao",
    },
    {
        "nome": "Gamificação Estrutural",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Gamificação Estrutural/Conteúdo"],
        "id_db": "imersiva_gamificacao",
    },
    {
        "nome": "Jogos Sérios com Blocos 3D",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Jogos Sérios 3D", "imersiva_jogos_serios_3d"],
        "id": "imersiva_jogos_serios_3d",
        "id_db": "imersiva_jogos_serios_3d",
    },
    {
        "nome": "Roleplay",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Roleplaying", "Jogo de Papéis", "imersiva_roleplaying"],
        "id": "imersiva_roleplaying",
        "id_db": "imersiva_roleplaying",
    },
    {
        "nome": "Simulações",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Simulação"],
    },
    {
        "nome": "Vivência Metodologia imersiva Multissensorial",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Vivência Imersiva Multissensorial"],
    },
    # --- Dedutivas (ex-ANALÍTICAS) ---
    {
        "nome": "Chatbots",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Bots personalizáveis"],
    },
    {
        "nome": "Diagnóstico Coletivo",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["analitica_diagnostico_coletivo", "checkout_exit_ticket"],
        "id": "analitica_diagnostico_coletivo",
        "id_db": "analitica_diagnostico_coletivo",
    },
    {
        "nome": "Dog or Cat: Reconhecimento de Imagens",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Dog or Cat"],
    },
    {
        "nome": "Extrato de Participação",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Extrato de Participações"],
    },
    {
        "nome": "Inteligência Artificial Generativa",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["IA Generativa"],
    },
    {"nome": "Mapa de Calor", "etiqueta": ETIQUETA_DEDUTIVAS},
    {
        "nome": "Metodologia analítica da Aprendizagem",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Analítica da Aprendizagem", "Learning Analytics", "analitica_learning_analytics"],
        "id": "analitica_learning_analytics",
        "id_db": "analitica_learning_analytics",
    },
    {"nome": "RAG", "etiqueta": ETIQUETA_DEDUTIVAS},
    {
        "nome": "Trilhas de Aprendizagem",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": [
            "Trilha de Aprendizagem Adaptativa",
            "Trilhas de Aprendizagem Adaptativas",
            "analitica_trilhas_adaptativas",
        ],
        "id": "analitica_trilhas_adaptativas",
        "id_db": "analitica_trilhas_adaptativas",
    },
)


def entradas_catalogo_dia() -> list[dict[str, Any]]:
    """Normaliza id e etiqueta pública para cada uma das 39."""
    out: list[dict[str, Any]] = []
    for raw in CATALOGO_METODOLOGIAS_DIA:
        nome = str(raw["nome"]).strip()
        mid = str(raw.get("id") or f"dia_{_slug(nome)}").strip()
        aliases = [str(a).strip() for a in (raw.get("aliases") or []) if str(a).strip()]
        etiqueta = str(raw.get("etiqueta") or "").strip() or ETIQUETA_INDUTIVAS
        # defesa: nunca vaziar rótulo autoral proibido
        etiqueta = etiqueta_publica(etiqueta, fallback=etiqueta)
        out.append(
            {
                "id": mid,
                "nome": nome,
                "etiqueta": etiqueta,
                "id_db": raw.get("id_db"),
                "aliases": aliases,
            }
        )
    return out
