"""
MAtivas - Diagnóstico por Árvore de Decisão (Claude via AWS Bedrock)
=====================================================================
Substitui a recomendação determinística de uma única metodologia por
navegação em árvore:

  Nível 1 (ramos): Criativas, Ágeis, Imersivas, Analíticas
  Nível 2 (folhas): metodologias cadastradas em problema_mativa

Em caso de falha na AWS, faz fallback para o matching por palavras-chave
(`diagnostico.diagnosticar`) enriquecido com alternativas do mesmo ramo.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import defaultdict
from typing import Any

from diagnostico import (
    GRUPO_TEXTOS,
    _montar_justificativa,
    _normalizar_grupo,
    _texto_grupo,
    diagnosticar,
    extrair_contexto,
)

logger = logging.getLogger("mativas.diagnostico_arvore")

# Ordem canônica dos ramos (Nível 1)
RAMOS_CANONICOS = (
    "Metodologias (Cri)ativas",
    "Metodologias Ágeis",
    "Metodologias Imersivas",
    "Metodologias Analíticas",
)

MODEL_ID = os.environ.get(
    "BEDROCK_DIAGNOSTICO_MODEL",
    "us.anthropic.claude-sonnet-4-20250514-v1:0",
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

SYSTEM_PROMPT_ARVORE = (
    "Você é um especialista em Metodologias Inov-ativas na Educação, com base "
    "exclusiva na obra de Andrea Filatro.\n\n"
    "{guardrails}"
    "Você deve raciocinar como uma ÁRVORE DE DECISÃO de dois níveis:\n"
    "  • Nível 1 (RAMOS / nós-pai): Criativas, Ágeis, Imersivas e Analíticas.\n"
    "  • Nível 2 (FOLHAS): metodologias específicas listadas no mapa abaixo.\n\n"
    "=== MAPA DA ÁRVORE (Ground Truth — use SOMENTE estas folhas) ===\n"
    "{arvore_metodologias}\n"
    "=== FIM DO MAPA ===\n\n"
    "PROCEDIMENTO OBRIGATÓRIO:\n"
    "1. Leia o desafio do professor.\n"
    "2. Escolha o RAMO (Nível 1) mais aderente.\n"
    "3. Dentro desse ramo, escolha a FOLHA (metodologia) que melhor resolve o "
    "desafio — este é o \"match_perfeito\". O campo \"nome\" DEVE ser uma "
    "metodologia listada no mapa, com grafia idêntica.\n"
    "4. Selecione 1 ou 2 folhas COLATERAIS do MESMO ramo (não repetir o match "
    "perfeito) para \"alternativas_mesmo_ramo\".\n"
    "5. Proponha uma \"fusao_estrategica\": combinação inovadora de DUAS "
    "metodologias do mapa (podem ser de ramos diferentes). Invente um nome "
    "criativo para a fusão e explique a sinergia.\n\n"
    "FORMATO DE SAÍDA (CONTRATO OBRIGATÓRIO):\n"
    "Responda ESTRITAMENTE em JSON válido, sem texto antes ou depois, sem "
    "blocos de código markdown. Estrutura EXATA:\n"
    "{{\n"
    '  "match_perfeito": {{\n'
    '    "nome": "<metodologia exata do mapa>",\n'
    '    "categoria": "<um dos 4 ramos canônicos>",\n'
    '    "justificativa": "<por que esta folha resolve o desafio>"\n'
    "  }},\n"
    '  "alternativas_mesmo_ramo": [\n'
    '    {{"nome": "<metodologia>", "categoria": "<mesmo ramo>", '
    '"justificativa": "<por que também funcionaria>"}}\n'
    "  ],\n"
    '  "fusao_estrategica": {{\n'
    '    "nome": "<nome criativo da fusão>",\n'
    '    "metodologias": ["<metodologia A>", "<metodologia B>"],\n'
    '    "categorias": ["<ramo A>", "<ramo B>"],\n'
    '    "sinergia": "<como as duas se complementam no desafio>"\n'
    "  }}\n"
    "}}\n"
)


def _ensure_services_path() -> None:
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    services_dir = os.path.join(project_root, "services")
    for path in (project_root, services_dir, backend_dir):
        if path not in sys.path:
            sys.path.insert(0, path)


def montar_arvore_metodologias(registros: list[dict] | None) -> str:
    """Agrupa metodologias ativas pelos 4 ramos e devolve texto estruturado."""
    por_ramo: dict[str, list[dict]] = defaultdict(list)

    for r in registros or []:
        grupo = _normalizar_grupo(r.get("grupo")) or "Metodologias Analíticas"
        if grupo not in RAMOS_CANONICOS:
            grupo = "Metodologias Analíticas"
        nome = (r.get("metodologia") or "").strip()
        if not nome:
            continue
        por_ramo[grupo].append(
            {
                "metodologia": nome,
                "problemas_combinados": r.get("problemas_combinados") or "",
                "observacao_automatizacao": r.get("observacao_automatizacao") or "",
                "publico_preferencial": r.get("publico_preferencial") or "",
                "modalidade_preferencial": r.get("modalidade_preferencial") or "",
            }
        )

    blocos = []
    for ramo in RAMOS_CANONICOS:
        folhas = por_ramo.get(ramo) or []
        linhas = [f"## RAMO: {ramo} ({len(folhas)} metodologias)"]
        if not folhas:
            linhas.append("  (nenhuma metodologia cadastrada neste ramo)")
        else:
            for f in folhas:
                linhas.append(f"  - FOLHA: {f['metodologia']}")
                if f["problemas_combinados"]:
                    linhas.append(f"    Indicada quando: {f['problemas_combinados']}")
                if f["observacao_automatizacao"]:
                    linhas.append(f"    Observação: {f['observacao_automatizacao']}")
                if f["publico_preferencial"]:
                    linhas.append(f"    Público: {f['publico_preferencial']}")
                if f["modalidade_preferencial"]:
                    linhas.append(f"    Modalidade: {f['modalidade_preferencial']}")
        blocos.append("\n".join(linhas))

    return "\n\n".join(blocos)


def _indice_metodologias(registros: list[dict] | None) -> dict[str, dict]:
    """Mapa nome_normalizado → registro (para validar folhas do LLM)."""
    idx = {}
    for r in registros or []:
        nome = (r.get("metodologia") or "").strip()
        if not nome:
            continue
        idx[_chave_met(nome)] = r
        idx[nome.lower()] = r
    return idx


def _chave_met(nome: str) -> str:
    return re.sub(r"\s+", " ", (nome or "").strip().lower())


def _resolver_metodologia(nome: str, indice: dict[str, dict]) -> dict | None:
    if not nome:
        return None
    return indice.get(_chave_met(nome)) or indice.get(nome.strip().lower())


def extrair_json(texto: str) -> dict:
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Resposta do modelo não contém JSON válido.")


def _folha_dict(nome: str, categoria: str, justificativa: str) -> dict:
    cat = _normalizar_grupo(categoria) or categoria
    return {
        "nome": nome,
        "categoria": cat,
        "justificativa": (justificativa or "").strip(),
    }


def normalizar_resposta_arvore(
    bruto: dict,
    registros: list[dict] | None,
    texto_usuario: str,
) -> dict:
    """Valida/normaliza o JSON do LLM e acrescenta campos de compatibilidade."""
    indice = _indice_metodologias(registros)
    contexto = extrair_contexto(texto_usuario)

    mp = bruto.get("match_perfeito") or {}
    nome_mp = (mp.get("nome") or "").strip()
    reg_mp = _resolver_metodologia(nome_mp, indice)
    if reg_mp:
        nome_mp = reg_mp["metodologia"]
        cat_mp = _normalizar_grupo(reg_mp.get("grupo")) or _normalizar_grupo(
            mp.get("categoria")
        )
    else:
        # Folha inválida → fallback keyword
        raise ValueError(f"Match perfeito fora do mapa: {nome_mp!r}")

    just_mp = (mp.get("justificativa") or "").strip() or _montar_justificativa(
        nome_mp, cat_mp
    )
    match_perfeito = _folha_dict(nome_mp, cat_mp, just_mp)

    alternativas = []
    for alt in bruto.get("alternativas_mesmo_ramo") or []:
        if not isinstance(alt, dict):
            continue
        nome_alt = (alt.get("nome") or "").strip()
        reg_alt = _resolver_metodologia(nome_alt, indice)
        if not reg_alt:
            continue
        nome_alt = reg_alt["metodologia"]
        if _chave_met(nome_alt) == _chave_met(nome_mp):
            continue
        cat_alt = _normalizar_grupo(reg_alt.get("grupo")) or cat_mp
        # Preferir colaterais do mesmo ramo
        if cat_alt != match_perfeito["categoria"]:
            continue
        alternativas.append(
            _folha_dict(
                nome_alt,
                cat_alt,
                (alt.get("justificativa") or "").strip()
                or f"Também pertence às {cat_alt} e pode atender aspectos do desafio.",
            )
        )
        if len(alternativas) >= 2:
            break

    # Completa alternativas do mesmo ramo via DB se o LLM trouxe menos de 1
    if len(alternativas) < 1:
        for r in registros or []:
            if _normalizar_grupo(r.get("grupo")) != match_perfeito["categoria"]:
                continue
            nome = (r.get("metodologia") or "").strip()
            if not nome or _chave_met(nome) == _chave_met(nome_mp):
                continue
            alternativas.append(
                _folha_dict(
                    nome,
                    match_perfeito["categoria"],
                    f"Abordagem colateral no ramo {match_perfeito['categoria']}.",
                )
            )
            if len(alternativas) >= 2:
                break

    fusao_bruta = bruto.get("fusao_estrategica") or {}
    mets_fusao = []
    cats_fusao = []
    for nome in fusao_bruta.get("metodologias") or []:
        reg = _resolver_metodologia(str(nome), indice)
        if not reg:
            continue
        mets_fusao.append(reg["metodologia"])
        cats_fusao.append(_normalizar_grupo(reg.get("grupo")) or "Metodologias Analíticas")
        if len(mets_fusao) >= 2:
            break

    if len(mets_fusao) < 2:
        # Completa com outra metodologia de ramo diferente, se possível
        for r in registros or []:
            nome = (r.get("metodologia") or "").strip()
            if not nome or any(_chave_met(nome) == _chave_met(m) for m in mets_fusao):
                continue
            if _chave_met(nome) == _chave_met(nome_mp):
                continue
            mets_fusao.append(nome)
            cats_fusao.append(
                _normalizar_grupo(r.get("grupo")) or "Metodologias Analíticas"
            )
            if len(mets_fusao) >= 2:
                break

    if len(mets_fusao) < 2 and len(alternativas) >= 1:
        mets_fusao = [nome_mp, alternativas[0]["nome"]]
        cats_fusao = [match_perfeito["categoria"], alternativas[0]["categoria"]]

    nome_fusao = (fusao_bruta.get("nome") or "").strip() or (
        f"Sinergia {mets_fusao[0]} + {mets_fusao[1]}" if len(mets_fusao) >= 2 else "Fusão estratégica"
    )
    sinergia = (fusao_bruta.get("sinergia") or "").strip() or (
        f"Combina {mets_fusao[0]} e {mets_fusao[1]} para ampliar o repertório "
        "pedagógico frente ao desafio relatado."
        if len(mets_fusao) >= 2
        else "Combinação de abordagens do mapa de metodologias inov-ativas."
    )

    fusao = {
        "nome": nome_fusao,
        "metodologias": mets_fusao[:2],
        "categorias": cats_fusao[:2],
        "sinergia": sinergia,
    }

    return {
        "match_perfeito": match_perfeito,
        "alternativas_mesmo_ramo": alternativas,
        "fusao_estrategica": fusao,
        # Compatibilidade com Cadastro / worker (lock-in do match por padrão)
        "metodologia": match_perfeito["nome"],
        "justificativa": match_perfeito["justificativa"],
        "grupo": match_perfeito["categoria"],
        "grupo_titulo": match_perfeito["categoria"],
        "grupo_descricao": _texto_grupo(match_perfeito["categoria"]),
        "contexto": contexto,
        "fonte": "bedrock_arvore",
    }


def _fallback_keyword(
    texto_usuario: str,
    registros: list[dict] | None,
    nivel: str | None = None,
    formato: str | None = None,
) -> dict:
    """Enriquece o diagnóstico por keywords no formato da árvore."""
    base = diagnosticar(texto_usuario, registros, nivel=nivel, formato=formato)
    cat = base.get("grupo") or "Metodologias Analíticas"
    nome = base.get("metodologia")

    alternativas = []
    for r in registros or []:
        if _normalizar_grupo(r.get("grupo")) != cat:
            continue
        n = (r.get("metodologia") or "").strip()
        if not n or _chave_met(n) == _chave_met(nome or ""):
            continue
        alternativas.append(
            _folha_dict(
                n,
                cat,
                f"Também faz parte das {cat} e pode atender o desafio sob outro ângulo.",
            )
        )
        if len(alternativas) >= 2:
            break

    outro_ramo = None
    for r in registros or []:
        g = _normalizar_grupo(r.get("grupo"))
        if g and g != cat:
            outro_ramo = r
            break

    mets = [nome]
    cats = [cat]
    if outro_ramo:
        mets.append(outro_ramo["metodologia"])
        cats.append(_normalizar_grupo(outro_ramo.get("grupo")) or cat)

    fusao = {
        "nome": f"Ponte {mets[0]}" + (f" × {mets[1]}" if len(mets) > 1 else ""),
        "metodologias": mets[:2],
        "categorias": cats[:2],
        "sinergia": (
            f"Une a profundidade de {mets[0]} com elementos de "
            f"{mets[1] if len(mets) > 1 else 'outra abordagem do mapa'} "
            "para responder ao desafio com repertório ampliado."
        ),
    }

    return {
        "match_perfeito": _folha_dict(
            nome, cat, base.get("justificativa") or _montar_justificativa(nome, cat)
        ),
        "alternativas_mesmo_ramo": alternativas,
        "fusao_estrategica": fusao,
        "metodologia": nome,
        "justificativa": base.get("justificativa"),
        "grupo": cat,
        "grupo_titulo": cat,
        "grupo_descricao": base.get("grupo_descricao") or _texto_grupo(cat),
        "contexto": base.get("contexto") or extrair_contexto(texto_usuario),
        "publico_preferencial": base.get("publico_preferencial"),
        "modalidade_preferencial": base.get("modalidade_preferencial"),
        "score": base.get("score"),
        "fonte": "keywords_fallback",
    }


def _montar_prompt_usuario(
    texto: str,
    nivel: str | None = None,
    formato: str | None = None,
) -> str:
    partes = [f"Desafio relatado pelo professor:\n{texto}"]
    if nivel:
        partes.append(f"Nível de ensino informado: {nivel}")
    if formato:
        partes.append(f"Formato da aula informado: {formato}")
    partes.append(
        "Navegue na árvore de decisão e responda apenas com o JSON solicitado."
    )
    return "\n\n".join(partes)


def _invocar_bedrock(system_prompt: str, user_prompt: str) -> str:
    """Invoca Claude via LangChain/Bedrock com resiliência de SSL local."""
    _ensure_services_path()
    import urllib3
    import boto3
    from langchain_aws import ChatBedrock
    from langchain_core.messages import HumanMessage, SystemMessage

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
        verify=False,
    )
    llm = ChatBedrock(
        model=MODEL_ID,
        region=AWS_REGION,
        model_kwargs={"temperature": 0.2, "max_tokens": 3072},
        client=bedrock_client,
    )
    resposta = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )
    return getattr(resposta, "content", None) or str(resposta)


def diagnosticar_com_arvore(
    texto_usuario: str,
    registros: list[dict] | None,
    nivel: str | None = None,
    formato: str | None = None,
) -> dict[str, Any]:
    """Diagnóstico principal: Bedrock (árvore) com fallback por keywords."""
    if not (registros or []):
        logger.warning("Base problema_mativa vazia — usando fallback keyword.")
        return _fallback_keyword(texto_usuario, registros, nivel, formato)

    try:
        _ensure_services_path()
        from guardrails import build_guardrails_prompt

        guardrails = build_guardrails_prompt()
        arvore = montar_arvore_metodologias(registros)
        system_prompt = SYSTEM_PROMPT_ARVORE.format(
            guardrails=guardrails,
            arvore_metodologias=arvore,
        )
        user_prompt = _montar_prompt_usuario(texto_usuario, nivel, formato)
        bruto_txt = _invocar_bedrock(system_prompt, user_prompt)
        bruto = extrair_json(bruto_txt)
        resultado = normalizar_resposta_arvore(bruto, registros, texto_usuario)
        logger.info(
            "Diagnóstico árvore OK: match=%s ramo=%s alts=%d",
            resultado["match_perfeito"]["nome"],
            resultado["match_perfeito"]["categoria"],
            len(resultado["alternativas_mesmo_ramo"]),
        )
        return resultado
    except Exception as exc:
        logger.exception(
            "Falha no diagnóstico Bedrock/árvore — fallback keywords. Motivo: %s",
            exc,
        )
        return _fallback_keyword(texto_usuario, registros, nivel, formato)


# ---------------------------------------------------------------------
# Diálogo de refinamento (feedback do professor → novas sugestões)
# ---------------------------------------------------------------------
SYSTEM_PROMPT_REFINO = (
    "Você é um especialista em Metodologias Inov-ativas na Educação, com base "
    "exclusiva na obra de Andrea Filatro.\n\n"
    "{guardrails}"
    "O professor já viu uma proposta metodológica e agora dialoga com você: "
    "ele indica qual aspecto da abordagem escolhida NÃO se adequa à realidade "
    "da turma ou do contexto.\n\n"
    "=== MAPA DA ÁRVORE (Ground Truth — use SOMENTE estas folhas) ===\n"
    "{arvore_metodologias}\n"
    "=== FIM DO MAPA ===\n\n"
    "PROCEDIMENTO:\n"
    "1. Leia o desafio original, a abordagem em discussão e o feedback do professor.\n"
    "2. Responda de forma empática e breve em \"resposta_dialogo\" (1–3 frases), "
    "reconhecendo a restrição sem usar termos proibidos pelos guardrails.\n"
    "3. Gere de 3 a 4 \"sugestoes\" distintas, adequadas ao feedback. Cada item "
    "deve ter justificativa própria explicando por que resolve o ponto levantado.\n"
    "4. Preferir folhas do mapa. Pode incluir no máximo UMA fusão (tipo \"fusao\") "
    "de duas metodologias do mapa.\n"
    "5. NÃO repita a mesma metodologia rejeitada, a menos que o feedback peça "
    "apenas um ajuste de aplicação (nesse caso explique o ajuste na justificativa).\n\n"
    "FORMATO DE SAÍDA (CONTRATO OBRIGATÓRIO):\n"
    "Responda ESTRITAMENTE em JSON válido, sem markdown:\n"
    "{{\n"
    '  "resposta_dialogo": "<reconhecimento breve do feedback>",\n'
    '  "sugestoes": [\n'
    "    {{\n"
    '      "nome": "<metodologia do mapa OU nome da fusão>",\n'
    '      "categoria": "<ramo canônico ou ramos unidos por +>",\n'
    '      "justificativa": "<por que esta opção atende o feedback>",\n'
    '      "tipo": "folha|fusao",\n'
    '      "metodologias": ["<só se tipo=fusao: duas folhas do mapa>"]\n'
    "    }}\n"
    "  ]\n"
    "}}\n"
)


def normalizar_sugestoes_refino(
    bruto: dict,
    registros: list[dict] | None,
    abordagem_atual: str | None = None,
) -> dict:
    """Valida sugestões do refino; garante justificativa em cada item."""
    indice = _indice_metodologias(registros)
    atual_key = _chave_met(abordagem_atual or "")
    sugestoes = []

    for item in bruto.get("sugestoes") or []:
        if not isinstance(item, dict):
            continue
        tipo = (item.get("tipo") or "folha").strip().lower()
        just = (item.get("justificativa") or "").strip()
        if not just:
            just = "Opção alinhada ao feedback e ao mapa de metodologias inov-ativas."

        if tipo == "fusao":
            mets = []
            cats = []
            for nome in item.get("metodologias") or []:
                reg = _resolver_metodologia(str(nome), indice)
                if not reg:
                    continue
                mets.append(reg["metodologia"])
                cats.append(
                    _normalizar_grupo(reg.get("grupo")) or "Metodologias Analíticas"
                )
                if len(mets) >= 2:
                    break
            if len(mets) < 2:
                continue
            nome_fusao = (item.get("nome") or "").strip() or f"{mets[0]} + {mets[1]}"
            sugestoes.append(
                {
                    "nome": nome_fusao,
                    "categoria": " + ".join(cats[:2]),
                    "justificativa": just,
                    "tipo": "fusao",
                    "metodologias": mets[:2],
                }
            )
        else:
            nome = (item.get("nome") or "").strip()
            reg = _resolver_metodologia(nome, indice)
            if not reg:
                continue
            nome = reg["metodologia"]
            if atual_key and _chave_met(nome) == atual_key:
                # Permite se a justificativa explicitamente ajustar a aplicação
                if "ajust" not in just.lower() and "adapta" not in just.lower():
                    continue
            cat = _normalizar_grupo(reg.get("grupo")) or _normalizar_grupo(
                item.get("categoria")
            )
            sugestoes.append(
                {
                    "nome": nome,
                    "categoria": cat,
                    "justificativa": just,
                    "tipo": "folha",
                    "metodologias": [nome],
                }
            )

        if len(sugestoes) >= 4:
            break

    resposta = (bruto.get("resposta_dialogo") or "").strip() or (
        "Entendi o ponto que não se adequa à sua realidade. "
        "Seguem novas opções da Biblioteca de Metodologias Inov-ativas."
    )

    if not sugestoes:
        raise ValueError("Nenhuma sugestão válida após normalização do refino.")

    primeira = sugestoes[0]
    return {
        "resposta_dialogo": resposta,
        "sugestoes": sugestoes,
        "metodologia": primeira["nome"],
        "justificativa": primeira["justificativa"],
        "grupo": primeira.get("categoria"),
        "fonte": "bedrock_refino",
    }


def _fallback_refino(
    texto_usuario: str,
    registros: list[dict] | None,
    abordagem_atual: str | None,
    feedback: str,
    nivel: str | None = None,
    formato: str | None = None,
) -> dict:
    """Fallback: novas folhas do mapa, preferindo outro ramo, com justificativa."""
    base = _fallback_keyword(texto_usuario, registros, nivel, formato)
    atual_key = _chave_met(abordagem_atual or "")
    cat_atual = None
    for r in registros or []:
        if _chave_met(r.get("metodologia") or "") == atual_key:
            cat_atual = _normalizar_grupo(r.get("grupo"))
            break

    sugestoes = []
    # 1–2 do mesmo ramo (exceto a rejeitada), 1–2 de outros ramos
    for r in registros or []:
        nome = (r.get("metodologia") or "").strip()
        if not nome or _chave_met(nome) == atual_key:
            continue
        cat = _normalizar_grupo(r.get("grupo")) or "Metodologias Analíticas"
        same = cat == cat_atual
        if same and sum(1 for s in sugestoes if s["categoria"] == cat_atual) >= 2:
            continue
        if not same and sum(1 for s in sugestoes if s["categoria"] != cat_atual) >= 2:
            continue
        sugestoes.append(
            {
                "nome": nome,
                "categoria": cat,
                "justificativa": (
                    "Considerando o feedback informado, "
                    + nome
                    + " (ramo "
                    + cat
                    + ") constitui uma alternativa da Biblioteca de Metodologias Inov-ativas mais alinhada a esta restricao."
                ),
                "tipo": "folha",
                "metodologias": [nome],
            }
        )
        if len(sugestoes) >= 4:
            break

    if len(sugestoes) < 2:
        for alt in base.get("alternativas_mesmo_ramo") or []:
            if _chave_met(alt["nome"]) == atual_key:
                continue
            sugestoes.append(
                {
                    "nome": alt["nome"],
                    "categoria": alt["categoria"],
                    "justificativa": alt["justificativa"],
                    "tipo": "folha",
                    "metodologias": [alt["nome"]],
                }
            )
            if len(sugestoes) >= 3:
                break

    fusao = base.get("fusao_estrategica") or {}
    if fusao.get("metodologias") and len(sugestoes) < 4:
        sugestoes.append(
            {
                "nome": fusao.get("nome") or "Fusão estratégica",
                "categoria": " + ".join(fusao.get("categorias") or []),
                "justificativa": fusao.get("sinergia")
                or "Combinação que amplia o repertório frente à restrição relatada.",
                "tipo": "fusao",
                "metodologias": fusao.get("metodologias") or [],
            }
        )

    return {
        "resposta_dialogo": (
            "Entendi o aspecto que não se adequa à sua realidade. "
            "Com base nisso, selecionei novas opções na Biblioteca de Metodologias Inov-ativas."
        ),
        "sugestoes": sugestoes[:4],
        "metodologia": sugestoes[0]["nome"] if sugestoes else base.get("metodologia"),
        "justificativa": sugestoes[0]["justificativa"] if sugestoes else base.get("justificativa"),
        "grupo": sugestoes[0]["categoria"] if sugestoes else base.get("grupo"),
        "fonte": "keywords_refino_fallback",
    }


def refinar_diagnostico_com_dialogo(
    texto_usuario: str,
    registros: list[dict] | None,
    *,
    abordagem_atual: str,
    feedback: str,
    categoria_atual: str | None = None,
    justificativa_atual: str | None = None,
    nivel: str | None = None,
    formato: str | None = None,
) -> dict[str, Any]:
    """Segundo turno: professor aponta inadequação → novas sugestões justificadas."""
    feedback = (feedback or "").strip()
    abordagem_atual = (abordagem_atual or "").strip()
    if not feedback:
        raise ValueError("Informe o aspecto que não se adequa à sua realidade.")
    if not abordagem_atual:
        raise ValueError("Informe a abordagem em discussão.")

    if not (registros or []):
        return _fallback_refino(
            texto_usuario, registros, abordagem_atual, feedback, nivel, formato
        )

    try:
        _ensure_services_path()
        from guardrails import build_guardrails_prompt

        guardrails = build_guardrails_prompt()
        arvore = montar_arvore_metodologias(registros)
        system_prompt = SYSTEM_PROMPT_REFINO.format(
            guardrails=guardrails,
            arvore_metodologias=arvore,
        )
        partes = [
            f"Desafio original do professor:\n{texto_usuario}",
            f"Abordagem em discussão: {abordagem_atual}",
        ]
        if categoria_atual:
            partes.append(f"Categoria/ramo dessa abordagem: {categoria_atual}")
        if justificativa_atual:
            partes.append(f"Justificativa original apresentada:\n{justificativa_atual}")
        if nivel:
            partes.append(f"Nível de ensino: {nivel}")
        if formato:
            partes.append(f"Formato da aula: {formato}")
        partes.append(
            "Feedback do professor (o que NÃO se adequa à realidade):\n" + feedback
        )
        partes.append(
            "Gere a resposta_dialogo e a lista de sugestões em JSON, "
            "cada uma com justificativa própria."
        )
        user_prompt = "\n\n".join(partes)

        bruto_txt = _invocar_bedrock(system_prompt, user_prompt)
        bruto = extrair_json(bruto_txt)
        resultado = normalizar_sugestoes_refino(bruto, registros, abordagem_atual)
        logger.info(
            "Refino diálogo OK: %d sugestões (abordagem=%s)",
            len(resultado.get("sugestoes") or []),
            abordagem_atual,
        )
        return resultado
    except Exception as exc:
        logger.exception("Falha no refino Bedrock — fallback. Motivo: %s", exc)
        return _fallback_refino(
            texto_usuario, registros, abordagem_atual, feedback, nivel, formato
        )
