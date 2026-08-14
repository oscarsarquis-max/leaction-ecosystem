"""Aliases dos nomes das 39 metodologias canônicas (School).

A 035 poliu `school_metodologias_catalogo.nome`. Curadoria, AEE, PEI e o
webhook B2C ainda amarram por texto. Este mapa devolve o `codigo` estável
para o rótulo antigo (e o atual) continuar encaixando no canônico.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# alias visível → codigo do catálogo. Inclui nome atual, nome pré-035 e
# rótulos que o Inove ainda pode enviar (EduScrum, Elevator Pitch, …).
ALIAS_PARA_CODIGO: dict[str, str] = {
    # Agilidade
    "método inove4us": "agil_eduscrum",
    "metodo inove4us": "agil_eduscrum",
    "eduscrum": "agil_eduscrum",
    "canvas mania": "agil_canvas_mania",
    "pitch de elevador": "agil_elevator_pitch",
    "discurso de elevador": "agil_elevator_pitch",
    "elevator pitch": "agil_elevator_pitch",
    "hackathon": "agil_hackathons",
    "hackathons": "agil_hackathons",
    "mapa mental": "agil_mapeamento_mental",
    "mapeamento mental": "agil_mapeamento_mental",
    "minute paper": "agil_minute_paper",
    "pecha kucha": "agil_pecha_kucha",
    "dupla piloto e navegador": "agil_pedagogia_extrema",
    "pedagogia extrema": "agil_pedagogia_extrema",
    # Contextuais
    "gamificação de conteúdo": "gamificacao_de_conteudo",
    "gamificacao de conteudo": "gamificacao_de_conteudo",
    "gamificação estrutural": "gamificacao_estrutural",
    "gamificacao estrutural": "gamificacao_estrutural",
    "gamificação estrutural/conteúdo": "gamificacao_estrutural",
    "aprendizagem baseada em jogos": "imersiva_aprendizagem_jogos",
    "escape room pedagógico": "imersiva_escape_room",
    "escape room pedagogico": "imersiva_escape_room",
    "escape room": "imersiva_escape_room",
    "escape room educacional": "imersiva_escape_room",
    "jogos sérios em ambiente 3d": "imersiva_jogos_serios_3d",
    "jogos serios em ambiente 3d": "imersiva_jogos_serios_3d",
    "jogos sérios com blocos 3d": "imersiva_jogos_serios_3d",
    "jogos sérios 3d": "imersiva_jogos_serios_3d",
    "roleplay (dramatização de papéis)": "imersiva_roleplaying",
    "roleplay (dramatizacao de papeis)": "imersiva_roleplaying",
    "roleplay": "imersiva_roleplaying",
    "roleplaying": "imersiva_roleplaying",
    "jogo de papéis": "imersiva_roleplaying",
    "simulação": "imersiva_simulacoes",
    "simulacao": "imersiva_simulacoes",
    "simulações": "imersiva_simulacoes",
    "vivência multissensorial": "imersiva_vivencia_multissensorial",
    "vivencia multissensorial": "imersiva_vivencia_multissensorial",
    "vivência imersiva multissensorial": "imersiva_vivencia_multissensorial",
    "vivência metodologia imersiva multissensorial": "imersiva_vivencia_multissensorial",
    # Dedutivas
    "chatbot pedagógico": "analitica_chatbots",
    "chatbot pedagogico": "analitica_chatbots",
    "chatbots": "analitica_chatbots",
    "bots personalizáveis": "analitica_chatbots",
    "diagnóstico coletivo": "analitica_diagnostico_coletivo",
    "diagnostico coletivo": "analitica_diagnostico_coletivo",
    "classificação de imagens (treino e teste)": "analitica_dog_or_cat",
    "classificacao de imagens (treino e teste)": "analitica_dog_or_cat",
    "dog or cat: reconhecimento de imagens": "analitica_dog_or_cat",
    "dog or cat": "analitica_dog_or_cat",
    "extrato de participação": "analitica_extrato_participacao",
    "extrato de participacao": "analitica_extrato_participacao",
    "extrato de participações": "analitica_extrato_participacao",
    "ia generativa na aula": "analitica_ia_generativa",
    "ia generativa": "analitica_ia_generativa",
    "inteligência artificial generativa": "analitica_ia_generativa",
    "inteligencia artificial generativa": "analitica_ia_generativa",
    "mapa de calor": "analitica_mapa_calor",
    "análise da aprendizagem": "analitica_learning_analytics",
    "analise da aprendizagem": "analitica_learning_analytics",
    "analítica da aprendizagem": "analitica_learning_analytics",
    "metodologia analítica da aprendizagem": "analitica_learning_analytics",
    "learning analytics": "analitica_learning_analytics",
    "pesquisa com fontes confiáveis (rag)": "analitica_rag",
    "pesquisa com fontes confiaveis (rag)": "analitica_rag",
    "rag": "analitica_rag",
    "trilhas adaptativas": "analitica_trilhas_adaptativas",
    "trilhas de aprendizagem": "analitica_trilhas_adaptativas",
    "trilhas de aprendizagem adaptativas": "analitica_trilhas_adaptativas",
    "trilha de aprendizagem adaptativa": "analitica_trilhas_adaptativas",
    # Indutivas
    "aprendizagem baseada em casos": "aprendizagem_baseada_em_casos",
    "caso empático": "aprendizagem_baseada_em_casos",
    "caso empatico": "aprendizagem_baseada_em_casos",
    "abordagem problematizadora": "criativa_abordagem_problematizadora",
    "aprendizagem baseada em equipes (tbl)": "criativa_aprendizagem_equipes",
    "aprendizagem baseada em equipes": "criativa_aprendizagem_equipes",
    "team-based learning": "criativa_aprendizagem_equipes",
    "tbl": "criativa_aprendizagem_equipes",
    "aprendizagem maker": "criativa_aprendizagem_maker",
    "coaching reverso": "criativa_coaching_reverso",
    "design thinking express": "criativa_design_thinking_express",
    "design thinking": "criativa_design_thinking_express",
    "dt express": "criativa_design_thinking_express",
    "mapa de polaridades": "criativa_mapa_polaridades",
    "narrativa transmídia (estações)": "criativa_narrativas_transmidia",
    "narrativa transmidia (estacoes)": "criativa_narrativas_transmidia",
    "narrativas transmídia": "criativa_narrativas_transmidia",
    "narrativas transmídia em rotação por estações": "criativa_narrativas_transmidia",
    "rotação por estações": "criativa_narrativas_transmidia",
    "painel de perspectivas diversas": "criativa_painel_diversidade",
    "painel da diversidade de perspectivas": "criativa_painel_diversidade",
    "painel de diversidade": "criativa_painel_diversidade",
    "aprendizagem baseada em problemas (pbl)": "criativa_pbl_problemas",
    "aprendizagem baseada em problemas": "criativa_pbl_problemas",
    "pbl": "criativa_pbl_problemas",
    "abp": "criativa_pbl_problemas",
    "aprendizagem baseada em projetos (pjbl)": "criativa_pbl_projetos",
    "aprendizagem baseada em projetos": "criativa_pbl_projetos",
    "pjbl": "criativa_pbl_projetos",
    "sala de aula invertida": "criativa_sala_invertida",
    "flipped classroom": "criativa_sala_invertida",
    "rotina veja · pense · pergunte · crie": "criativa_veja_pense_pergunte_crie",
    "rotina veja-pense-pergunte-crie": "criativa_veja_pense_pergunte_crie",
    "world café": "criativa_world_cafe",
    "world cafe": "criativa_world_cafe",
}


def norm_alias(valor: str | None) -> str:
    return " ".join(str(valor or "").strip().lower().split())


def slug_alias(valor: str | None) -> str:
    raw = unicodedata.normalize("NFKD", str(valor or ""))
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", raw.lower())


_SLUG_PARA_CODIGO: dict[str, str] = {}
for _alias, _codigo in ALIAS_PARA_CODIGO.items():
    _key = slug_alias(_alias)
    if _key and _key not in _SLUG_PARA_CODIGO:
        _SLUG_PARA_CODIGO[_key] = _codigo


def codigo_por_nome(nome: str | None) -> str | None:
    token = str(nome or "").strip()
    if not token:
        return None
    hit = ALIAS_PARA_CODIGO.get(norm_alias(token))
    if hit:
        return hit
    if token.replace("-", "_").replace(".", "").isidentifier() or "_" in token:
        return token
    return _SLUG_PARA_CODIGO.get(slug_alias(token))


def aliases_do_codigo(codigo: str | None) -> list[str]:
    key = str(codigo or "").strip()
    if not key:
        return []
    return sorted({alias for alias, cod in ALIAS_PARA_CODIGO.items() if cod == key})


def fetch_catalogo(
    cur: Any,
    *,
    nome: str | None = None,
    codigo: str | None = None,
    instituicao_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve id/nome/codigo no catálogo canônico (nome atual, alias ou codigo)."""
    inst = str(instituicao_id or "").strip() or None
    wanted = str(codigo or "").strip() or codigo_por_nome(nome)
    if wanted:
        cur.execute(
            """
            SELECT id, nome, codigo
            FROM public.school_metodologias_catalogo
            WHERE ativo IS TRUE
              AND (
                    lower(codigo) = lower(%s)
                 OR lower(trim(nome)) = lower(trim(%s))
              )
            ORDER BY CASE WHEN origem = 'escola' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (wanted, wanted),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

    token = str(nome or "").strip()
    if not token:
        return None
    cur.execute(
        """
        SELECT id, nome, codigo
        FROM public.school_metodologias_catalogo
        WHERE ativo IS TRUE
          AND (
                lower(trim(nome)) = lower(trim(%s))
             OR lower(codigo) = lower(%s)
          )
          AND (
                COALESCE(origem, '') IN (
                    'inove4us', 'padrao', 'referencia_inove4us', 'escola'
                )
             OR instituicao_origem_id IS NOT DISTINCT FROM %s::uuid
          )
        ORDER BY CASE WHEN origem = 'escola' THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (token, token, inst),
    )
    row = cur.fetchone()
    return dict(row) if row else None
