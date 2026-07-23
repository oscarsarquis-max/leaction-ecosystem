"""
Catálogo canônico de dinâmicas do vetor Dia a Dia (39 nomes).

Espelha a base da obra usada na MAtivas — apenas nomes, sem categorias autorais.
Não importa código de outra app; a lista é local e versionada aqui.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _slug(nome: str) -> str:
    raw = unicodedata.normalize("NFKD", nome or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = raw.lower().strip()
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return raw or "dinamica"


# 39 metodologias — ordem alfabética na UI é aplicada no serviço.
# `id_db` (opcional): id em METODOLOGIAS_DB para enriquecer descrição / manter compat.
# `aliases`: nomes/ids alternativos pesquisáveis e resolvíveis.
CATALOGO_METODOLOGIAS_DIA: tuple[dict[str, Any], ...] = (
    {
        "nome": "Abordagem Problematizadora",
    },
    {
        "nome": "Aprendizagem Baseada em Casos",
        "aliases": ["Caso Empático", "criativa_caso_empatico"],
        "id_db": "criativa_caso_empatico",
    },
    {
        "nome": "Aprendizagem Baseada em Equipes",
        "aliases": ["Team-Based Learning", "TBL"],
    },
    {
        "nome": "Aprendizagem Baseada em Jogos",
    },
    {
        "nome": "Aprendizagem Baseada em Problemas",
        "aliases": ["PBL", "ABP", "Aprendizagem Baseada em Problemas (PBL)"],
    },
    {
        "nome": "Aprendizagem Baseada em Projetos",
    },
    {
        "nome": "Aprendizagem Maker",
    },
    {
        "nome": "Canvas Mania",
    },
    {
        "nome": "Chatbots",
        "aliases": ["Bots personalizáveis"],
    },
    {
        "nome": "Coaching Reverso",
    },
    {
        "nome": "Design Thinking",
        "aliases": ["Design Thinking Express", "DT Express", "ideacao_brainstorming_guiado"],
        "id": "criativa_design_thinking_express",
        "id_db": "criativa_design_thinking_express",
    },
    {
        "nome": "Diagnóstico Coletivo",
        "aliases": ["analitica_diagnostico_coletivo", "checkout_exit_ticket"],
        "id": "analitica_diagnostico_coletivo",
        "id_db": "analitica_diagnostico_coletivo",
    },
    {
        "nome": "Discurso de Elevador",
        "aliases": ["Elevator Pitch", "agil_elevator_pitch"],
        "id": "agil_elevator_pitch",
        "id_db": "agil_elevator_pitch",
    },
    {
        "nome": "Dog or Cat: Reconhecimento de Imagens",
        "aliases": ["Dog or Cat"],
    },
    {
        "nome": "EduScrum",
    },
    {
        "nome": "Escape Room",
        "aliases": ["Escape Room Educacional", "imersiva_escape_room"],
        "id": "imersiva_escape_room",
        "id_db": "imersiva_escape_room",
    },
    {
        "nome": "Extrato de Participação",
        "aliases": ["Extrato de Participações"],
    },
    {
        "nome": "Gamificação de Conteúdo",
        "aliases": ["imersiva_gamificacao"],
        "id_db": "imersiva_gamificacao",
    },
    {
        "nome": "Gamificação Estrutural",
        "aliases": ["Gamificação Estrutural/Conteúdo"],
        "id_db": "imersiva_gamificacao",
    },
    {
        "nome": "Hackathons",
        "aliases": ["Hackathon"],
    },
    {
        "nome": "Inteligência Artificial Generativa",
        "aliases": ["IA Generativa"],
    },
    {
        "nome": "Jogos Sérios com Blocos 3D",
        "aliases": ["Jogos Sérios 3D", "imersiva_jogos_serios_3d"],
        "id": "imersiva_jogos_serios_3d",
        "id_db": "imersiva_jogos_serios_3d",
    },
    {
        "nome": "Mapa de Calor",
    },
    {
        "nome": "Mapa de Polaridades",
    },
    {
        "nome": "Mapeamento mental",
        "aliases": ["Mapeamento Mental"],
    },
    {
        "nome": "Metodologia analítica da Aprendizagem",
        "aliases": ["Analítica da Aprendizagem", "Learning Analytics", "analitica_learning_analytics"],
        "id": "analitica_learning_analytics",
        "id_db": "analitica_learning_analytics",
    },
    {
        "nome": "Minute Paper",
        "aliases": ["agil_minute_paper", "rapido_minute_paper"],
        "id": "agil_minute_paper",
        "id_db": "agil_minute_paper",
    },
    {
        "nome": "Narrativas Transmídia em Rotação por Estações",
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
        "aliases": ["Painel de Diversidade", "criativa_painel_diversidade"],
        "id": "criativa_painel_diversidade",
        "id_db": "criativa_painel_diversidade",
    },
    {
        "nome": "Pecha Kucha",
        "aliases": ["agil_pecha_kucha"],
        "id": "agil_pecha_kucha",
        "id_db": "agil_pecha_kucha",
    },
    {
        "nome": "Pedagogia Extrema",
    },
    {
        "nome": "RAG",
    },
    {
        "nome": "Roleplay",
        "aliases": ["Roleplaying", "Jogo de Papéis", "imersiva_roleplaying"],
        "id": "imersiva_roleplaying",
        "id_db": "imersiva_roleplaying",
    },
    {
        "nome": "Rotina Veja-Pense-Pergunte-Crie",
    },
    {
        "nome": "Sala de Aula Invertida",
        "aliases": ["Flipped Classroom"],
    },
    {
        "nome": "Simulações",
        "aliases": ["Simulação"],
    },
    {
        "nome": "Trilhas de Aprendizagem",
        "aliases": [
            "Trilha de Aprendizagem Adaptativa",
            "Trilhas de Aprendizagem Adaptativas",
            "analitica_trilhas_adaptativas",
        ],
        "id": "analitica_trilhas_adaptativas",
        "id_db": "analitica_trilhas_adaptativas",
    },
    {
        "nome": "Vivência Metodologia imersiva Multissensorial",
        "aliases": ["Vivência Imersiva Multissensorial"],
    },
    {
        "nome": "World Café",
        "aliases": ["World Cafe"],
    },
)


def entradas_catalogo_dia() -> list[dict[str, Any]]:
    """Normaliza id (explícito ou slug do nome) para cada uma das 39."""
    out: list[dict[str, Any]] = []
    for raw in CATALOGO_METODOLOGIAS_DIA:
        nome = str(raw["nome"]).strip()
        mid = str(raw.get("id") or f"dia_{_slug(nome)}").strip()
        aliases = [str(a).strip() for a in (raw.get("aliases") or []) if str(a).strip()]
        out.append(
            {
                "id": mid,
                "nome": nome,
                "id_db": raw.get("id_db"),
                "aliases": aliases,
            }
        )
    return out
