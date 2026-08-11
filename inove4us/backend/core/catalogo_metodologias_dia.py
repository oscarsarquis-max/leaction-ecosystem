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
    {
        "nome": "Abordagem Problematizadora",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_abordagem_problematizadora",
        "id_db": "criativa_abordagem_problematizadora",
    },
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
        "id": "criativa_aprendizagem_equipes",
        "id_db": "criativa_aprendizagem_equipes",
    },
    {
        "nome": "Aprendizagem Baseada em Problemas",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["PBL", "ABP", "Aprendizagem Baseada em Problemas (PBL)"],
        "id": "criativa_pbl_problemas",
        "id_db": "criativa_pbl_problemas",
    },
    {
        "nome": "Aprendizagem Baseada em Projetos",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_pbl_projetos",
        "id_db": "criativa_pbl_projetos",
    },
    {
        "nome": "Aprendizagem Maker",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_aprendizagem_maker",
        "id_db": "criativa_aprendizagem_maker",
    },
    {
        "nome": "Coaching Reverso",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_coaching_reverso",
        "id_db": "criativa_coaching_reverso",
    },
    {
        "nome": "Design Thinking",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Design Thinking Express", "DT Express", "ideacao_brainstorming_guiado"],
        "id": "criativa_design_thinking_express",
        "id_db": "criativa_design_thinking_express",
    },
    {
        "nome": "Mapa de Polaridades",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_mapa_polaridades",
        "id_db": "criativa_mapa_polaridades",
    },
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
    {
        "nome": "Rotina Veja-Pense-Pergunte-Crie",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "id": "criativa_veja_pense_pergunte_crie",
        "id_db": "criativa_veja_pense_pergunte_crie",
    },
    {
        "nome": "Sala de Aula Invertida",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["Flipped Classroom"],
        "id": "criativa_sala_invertida",
        "id_db": "criativa_sala_invertida",
    },
    {
        "nome": "World Café",
        "etiqueta": ETIQUETA_INDUTIVAS,
        "aliases": ["World Cafe"],
        "id": "criativa_world_cafe",
        "id_db": "criativa_world_cafe",
    },
    # --- Agilidade (ex-ÁGEIS) ---
    {
        "nome": "Canvas Mania",
        "etiqueta": ETIQUETA_AGILIDADE,
        "id": "agil_canvas_mania",
        "id_db": "agil_canvas_mania",
    },
    {
        "nome": "Discurso de Elevador",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Elevator Pitch", "agil_elevator_pitch"],
        "id": "agil_elevator_pitch",
        "id_db": "agil_elevator_pitch",
    },
    {
        "nome": "EduScrum",
        "etiqueta": ETIQUETA_AGILIDADE,
        "id": "agil_eduscrum",
        "id_db": "agil_eduscrum",
    },
    {
        "nome": "Hackathons",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Hackathon"],
        "id": "agil_hackathons",
        "id_db": "agil_hackathons",
    },
    {
        "nome": "Mapeamento mental",
        "etiqueta": ETIQUETA_AGILIDADE,
        "aliases": ["Mapeamento Mental"],
        "id": "agil_mapeamento_mental",
        "id_db": "agil_mapeamento_mental",
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
    {
        "nome": "Pedagogia Extrema",
        "etiqueta": ETIQUETA_AGILIDADE,
        "id": "agil_pedagogia_extrema",
        "id_db": "agil_pedagogia_extrema",
    },
    # --- Contextuais (ex-IMERSIVAS) ---
    {
        "nome": "Aprendizagem Baseada em Jogos",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "id": "imersiva_aprendizagem_jogos",
        "id_db": "imersiva_aprendizagem_jogos",
    },
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
        "id": "imersiva_simulacoes",
        "id_db": "imersiva_simulacoes",
    },
    {
        "nome": "Vivência Metodologia imersiva Multissensorial",
        "etiqueta": ETIQUETA_CONTEXTUAIS,
        "aliases": ["Vivência Imersiva Multissensorial"],
        "id": "imersiva_vivencia_multissensorial",
        "id_db": "imersiva_vivencia_multissensorial",
    },
    # --- Dedutivas (ex-ANALÍTICAS) ---
    {
        "nome": "Chatbots",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Bots personalizáveis"],
        "id": "analitica_chatbots",
        "id_db": "analitica_chatbots",
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
        "id": "analitica_dog_or_cat",
        "id_db": "analitica_dog_or_cat",
    },
    {
        "nome": "Extrato de Participação",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Extrato de Participações"],
        "id": "analitica_extrato_participacao",
        "id_db": "analitica_extrato_participacao",
    },
    {
        "nome": "Inteligência Artificial Generativa",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["IA Generativa"],
        "id": "analitica_ia_generativa",
        "id_db": "analitica_ia_generativa",
    },
    {
        "nome": "Mapa de Calor",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "id": "analitica_mapa_calor",
        "id_db": "analitica_mapa_calor",
    },
    {
        "nome": "Metodologia analítica da Aprendizagem",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "aliases": ["Analítica da Aprendizagem", "Learning Analytics", "analitica_learning_analytics"],
        "id": "analitica_learning_analytics",
        "id_db": "analitica_learning_analytics",
    },
    {
        "nome": "RAG",
        "etiqueta": ETIQUETA_DEDUTIVAS,
        "id": "analitica_rag",
        "id_db": "analitica_rag",
    },
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

# Sinais pedagógicos para matcher diagnóstico (não expostos na UI).
# Chave = id canônico (ou o id gerado por slug quando a entrada não declara id).
# Preferência: keywords inline em cada entrada; este mapa completa/override sem duplicar o catálogo.
KEYWORDS_POR_ID: dict[str, tuple[str, ...]] = {
    "criativa_abordagem_problematizadora": (
        "problematizar",
        "contradição",
        "questão geradora",
        "conscientização",
        "diálogo",
        "realidade social",
        "crítica",
        "transformação",
    ),
    "dia_aprendizagem_baseada_em_casos": (
        "caso",
        "narrativa clínica",
        "estudo de caso",
        "dilema",
        "decisão",
        "evidência",
        "analogia",
        "cenário real",
    ),
    "criativa_aprendizagem_equipes": (
        "equipe",
        "papéis",
        "trabalho em equipe",
        "TBL",
        "responsabilidade coletiva",
        "discussão em grupo",
        "preparação individual",
        "aplicação em equipe",
    ),
    "criativa_pbl_problemas": (
        "problema",
        "investigação",
        "investigar",
        "hipótese",
        "diagnóstico",
        "pesquisa",
        "tomada de decisão",
        "caso problema",
        "solução fundamentada",
    ),
    "criativa_pbl_projetos": (
        "projeto",
        "problema real",
        "investigação",
        "investigar",
        "solução",
        "produto final",
        "interdisciplinar",
        "comunidade",
        "longo prazo",
        "semestre",
        "desafio",
        "apresentação",
        "apresentar",
        "intervenção",
        "mapear",
    ),
    "criativa_aprendizagem_maker": (
        "maker",
        "prototipar",
        "construir",
        "mão na massa",
        "oficina",
        "artefato",
        "fabricação",
        "materiais",
        "teste físico",
    ),
    "criativa_coaching_reverso": (
        "coaching",
        "aluno ensina",
        "explicar para o outro",
        "mentoria entre pares",
        "feedback invertido",
        "autonomia",
        "mediação",
    ),
    "criativa_design_thinking_express": (
        "empatia",
        "usuário",
        "necessidade",
        "ideação",
        "protótipo",
        "teste",
        "problema aberto",
        "persona",
        "iteração",
    ),
    "criativa_mapa_polaridades": (
        "polaridade",
        "tensão",
        "ambos/e",
        "dilema",
        "contraste",
        "mapa",
        "equilíbrio",
        "perspectivas opostas",
    ),
    "criativa_narrativas_transmidia": (
        "narrativa",
        "estações",
        "rotação",
        "transmídia",
        "história",
        "múltiplos meios",
        "percurso",
        "continuidade narrativa",
    ),
    "criativa_painel_diversidade": (
        "perspectivas",
        "diversidade",
        "painel",
        "múltiplos olhares",
        "escuta",
        "representatividade",
        "ângulos diferentes",
    ),
    "criativa_veja_pense_pergunte_crie": (
        "veja",
        "pense",
        "pergunte",
        "crie",
        "rotina de pensamento",
        "observação",
        "curiosidade",
        "criação",
    ),
    "criativa_sala_invertida": (
        "estudo prévio",
        "antes da aula",
        "vídeo",
        "leitura prévia",
        "preparação",
        "flipped",
        "discussão em aula",
        "aplicação em aula",
        "conteúdo em casa",
    ),
    "criativa_world_cafe": (
        "world café",
        "rodadas de conversa",
        "mesas",
        "discussão em pares",
        "votação",
        "questão conceitual",
        "síntese coletiva",
        "hospedeiro de mesa",
        "nova votação",
    ),
    "agil_canvas_mania": (
        "canvas",
        "quadro visual",
        "preencher blocos",
        "modelo de negócio",
        "mapa visual",
        "síntese visual",
        "post-it",
    ),
    "agil_elevator_pitch": (
        "pitch",
        "60 segundos",
        "discurso curto",
        "elevator",
        "persuasão",
        "síntese oral",
        "banca",
        "apresentação rápida",
    ),
    "agil_eduscrum": (
        "scrum",
        "sprint",
        "kanban",
        "backlog",
        "daily",
        "papéis ágeis",
        "timebox",
        "incremento",
        "retrospectiva",
    ),
    "agil_hackathons": (
        "hackathon",
        "maratona",
        "desafio cronometrado",
        "protótipo rápido",
        "competição criativa",
        "entrega em horas",
        "pitch final",
    ),
    "agil_mapeamento_mental": (
        "mapa mental",
        "brainstorm",
        "associações",
        "organizar ideias",
        "ramificações",
        "visão geral",
        "conexões",
    ),
    "agil_minute_paper": (
        "minute paper",
        "um minuto",
        "escrita rápida",
        "checagem de compreensão",
        "saída rápida",
        "síntese curta",
        "ticket de saída",
    ),
    "agil_pecha_kucha": (
        "pecha kucha",
        "20 slides",
        "tempo fixo",
        "apresentação ritmada",
        "oratória",
        "slides automáticos",
    ),
    "agil_pedagogia_extrema": (
        "ciclos curtos",
        "feedback imediato",
        "entrega frequente",
        "pair",
        "iteração rápida",
        "extremo",
        "prática intensiva",
    ),
    "imersiva_aprendizagem_jogos": (
        "jogo",
        "regras",
        "partida",
        "mecânica de jogo",
        "desafio lúdico",
        "placar",
        "jogabilidade",
    ),
    "imersiva_escape_room": (
        "escape room",
        "enigmas",
        "pistas",
        "missão",
        "sala temática",
        "destravar",
        "tempo limite",
        "quebra-cabeça",
    ),
    "dia_gamificacao_de_conteudo": (
        "gamificação",
        "conteúdo jogável",
        "níveis de conteúdo",
        "missões de estudo",
        "desafios temáticos",
        "recompensas de aprendizagem",
    ),
    "dia_gamificacao_estrutural": (
        "pontos",
        "badges",
        "ranking",
        "níveis",
        "recompensas",
        "progresso",
        "estrutura de jogo",
        "engajamento por pontos",
    ),
    "imersiva_jogos_serios_3d": (
        "blocos 3d",
        "jogo sério",
        "construção espacial",
        "modelagem",
        "manipulação",
        "simulação tátil",
    ),
    "imersiva_roleplaying": (
        "roleplay",
        "papel",
        "encenação",
        "personagem",
        "simular situação",
        "debate encenado",
        "representação",
    ),
    "imersiva_simulacoes": (
        "simulação",
        "cenário simulado",
        "variáveis",
        "modelo",
        "experimento controlado",
        "o que acontece se",
        "ambiente simulado",
    ),
    "imersiva_vivencia_multissensorial": (
        "multissensorial",
        "vivência",
        "sentidos",
        "experiência imersiva",
        "corpo",
        "percepção",
        "imersão",
    ),
    "analitica_chatbots": (
        "chatbot",
        "bot",
        "conversa automatizada",
        "assistente",
        "diálogo com máquina",
        "perguntas e respostas",
    ),
    "analitica_diagnostico_coletivo": (
        "diagnóstico coletivo",
        "levantamento",
        "mapeamento coletivo",
        "sintomas",
        "causas coletivas",
        "visão compartilhada",
        "painel diagnóstico",
    ),
    "analitica_dog_or_cat": (
        "reconhecimento de imagens",
        "classificação visual",
        "dataset",
        "treinar modelo",
        "visão computacional",
        "rótulos",
        "imagens",
    ),
    "analitica_extrato_participacao": (
        "participação",
        "registro de contribuições",
        "extrato",
        "frequência de fala",
        "evidência de participação",
        "histórico individual",
    ),
    "analitica_ia_generativa": (
        "ia generativa",
        "prompt",
        "gerar texto",
        "chatgpt",
        "modelo generativo",
        "co-criação com ia",
        "revisar saída da ia",
    ),
    "analitica_mapa_calor": (
        "mapa de calor",
        "heatmap",
        "zonas de calor",
        "mapear",
        "focos",
        "concentração",
        "densidade",
        "visualização de dados",
        "hotspots",
    ),
    "analitica_learning_analytics": (
        "analytics",
        "dados de aprendizagem",
        "indicadores",
        "dashboard",
        "métricas",
        "desempenho",
        "rastreamento",
    ),
    "analitica_rag": (
        "rag",
        "recuperação de informação",
        "base de documentos",
        "consulta a fontes",
        "contexto recuperado",
        "busca semântica",
    ),
    "analitica_trilhas_adaptativas": (
        "trilha",
        "percurso adaptativo",
        "personalização",
        "níveis de dificuldade",
        "caminho individual",
        "sequência adaptativa",
        "ritmo próprio",
    ),
}


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
        # keywords: inline na entrada (se houver) ou mapa canônico por id
        kw_inline = [str(k).strip() for k in (raw.get("keywords") or []) if str(k).strip()]
        kw_mapa = list(KEYWORDS_POR_ID.get(mid) or ())
        keywords = kw_inline or kw_mapa
        out.append(
            {
                "id": mid,
                "nome": nome,
                "etiqueta": etiqueta,
                "id_db": raw.get("id_db"),
                "aliases": aliases,
                "keywords": keywords,
            }
        )
    return out


_ENTRADAS_CACHE: list[dict[str, Any]] | None = None
_INDEX_CACHE: dict[str, dict[str, Any]] | None = None


def _entradas_cached() -> list[dict[str, Any]]:
    global _ENTRADAS_CACHE
    if _ENTRADAS_CACHE is None:
        _ENTRADAS_CACHE = entradas_catalogo_dia()
    return _ENTRADAS_CACHE


def _index_catalogo() -> dict[str, dict[str, Any]]:
    """Índice por id, id_db, nome e aliases (chave normalizada)."""
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    idx: dict[str, dict[str, Any]] = {}
    for entrada in _entradas_cached():
        keys = {
            entrada["id"],
            _norm(entrada["id"]),
            _norm(entrada["nome"]),
        }
        id_db = entrada.get("id_db")
        if id_db:
            keys.add(str(id_db))
            keys.add(_norm(str(id_db)))
        for alias in entrada.get("aliases") or []:
            keys.add(str(alias))
            keys.add(_norm(str(alias)))
        for k in keys:
            if k and k not in idx:
                idx[k] = entrada
    _INDEX_CACHE = idx
    return idx


def resolver_entrada_catalogo(nome_ou_id: str | None) -> dict[str, Any] | None:
    """Resolve nome, alias ou id para uma das 39 entradas do catálogo canônico."""
    if not nome_ou_id:
        return None
    raw = str(nome_ou_id).strip()
    if not raw:
        return None
    idx = _index_catalogo()
    hit = idx.get(raw) or idx.get(_norm(raw))
    if hit:
        return hit
    # match parcial só em nomes/aliases longos (≥ 8) para evitar colisões
    key = _norm(raw)
    if len(key) < 8:
        return None
    for entrada in _entradas_cached():
        candidatos = [_norm(entrada["nome"])] + [
            _norm(a) for a in (entrada.get("aliases") or [])
        ]
        for c in candidatos:
            if len(c) >= 8 and (key in c or c in key):
                return entrada
    return None


def ids_catalogo_por_etiqueta(etiqueta: str) -> list[str]:
    alvo = etiqueta_publica(etiqueta)
    return [e["id"] for e in _entradas_cached() if e.get("etiqueta") == alvo]


def total_metodologias_catalogo() -> int:
    return len(_entradas_cached())
