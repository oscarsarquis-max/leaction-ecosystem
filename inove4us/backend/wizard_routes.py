"""Wizard Mesa do Inovador — fluxo guiado (problema → EduScrum).

Usa o DB configurado em DB_NAME (local: inove4us) e a base
ctdi_problemas_referencia para ancorar a análise.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys

import boto3
from botocore.config import Config
from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from core.metodologias_db import (
    aplicar_ganchos,
    duracao_total_cards,
    get_metodologia,
    get_metodologia_por_nome,
    resolve_metodologia_id,
)
from db import consumir_credito_ia, get_conn, get_creditos_ia
from prompts.inov_ativas import LISTA_FLAT, build_estruturar_system_prompt


def _normalizar_nome_metodologia(nome: str | None) -> str | None:
    """Alinha variações do modelo ao nome exato do framework."""
    if not nome:
        return nome
    raw = str(nome).strip()
    if raw in LISTA_FLAT:
        return raw
    low = raw.lower()
    aliases = {
        "gamificação estrutural": "Gamificação Estrutural/Conteúdo",
        "gamificacao estrutural": "Gamificação Estrutural/Conteúdo",
        "gamificação de conteúdo": "Gamificação Estrutural/Conteúdo",
        "gamificacao de conteudo": "Gamificação Estrutural/Conteúdo",
        "pecha-kucha": "Pecha Kucha",
        "escape room": "Escape Room Educacional",
        "escape-room educacional": "Escape Room Educacional",
        "design thinking": "Design Thinking Express",
        "role playing": "Roleplaying",
        "role-playing": "Roleplaying",
    }
    if low in aliases:
        return aliases[low]
    for oficial in LISTA_FLAT:
        if oficial.lower() == low or oficial.lower() in low or low in oficial.lower():
            return oficial
    return raw

wizard_bp = Blueprint("wizard", __name__)

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
# Arquitetura híbrida: 1 chamada curta (roteador A/B/C + ganchos). Cards vêm do DB.
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2000"))
WIZARD_REF_LIMIT = int(os.environ.get("WIZARD_REF_LIMIT", "3"))
# Vazio = BEDROCK_MODEL_ID.
WIZARD_BEDROCK_MODEL_ID = os.environ.get("WIZARD_BEDROCK_MODEL_ID", "").strip()
_DEFAULT_METODOLOGIA_ID = "criativa_rotacao_estacoes"


def _invoke_estruturar_bedrock(
    *,
    bedrock,
    model_id: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int,
    json_prefill: str = "{",
) -> dict:
    """Chama Bedrock e devolve dict JSON parseado. Levanta se truncar/inválido."""
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            # Haiku 4.5 rejeita temperature+top_p juntos.
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": json_prefill},
            ],
        }
    )
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    body_json = json.loads(response.get("body").read())
    texto_modelo = body_json["content"][0]["text"]
    stop_reason = body_json.get("stop_reason")
    usage = body_json.get("usage") or {}
    print(
        f"[wizard] model={model_id} stop={stop_reason} "
        f"out_tokens={usage.get('output_tokens')} in_tokens={usage.get('input_tokens')}",
        file=sys.stderr,
    )
    texto = _reconstruir_json_prefill(texto_modelo, json_prefill)
    try:
        return _extrair_json(texto)
    except Exception as parse_exc:
        if stop_reason == "max_tokens":
            raise ValueError(
                f"Resposta truncada (max_tokens); JSON incompleto: {parse_exc}"
            ) from parse_exc
        raise


def _bedrock_ssl_verify_enabled() -> bool:
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _get_bedrock_runtime_client():
    verify = _bedrock_ssl_verify_enabled()
    if not verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        # Ranking híbrido (JSON curto) — timeout menor que a antiga geração densa.
        config=Config(connect_timeout=8, read_timeout=60, retries={"max_attempts": 1}),
    )


def _reconstruir_json_prefill(texto: str, prefill: str = "{") -> str:
    """Reanexa o prefill do assistant (não vem no content da resposta Bedrock)."""
    limpo = (texto or "").strip()
    if not limpo:
        raise ValueError("Resposta vazia do modelo.")
    # Se o modelo já devolveu o objeto completo, não duplica a chave de abertura.
    if limpo.startswith(prefill):
        return limpo
    return prefill + limpo


def _extrair_json(texto: str) -> dict:
    if not texto:
        raise ValueError("Resposta vazia do modelo.")
    limpo = texto.strip()
    cerca = re.match(r"^```(?:json)?\s*(.*?)\s*```$", limpo, re.DOTALL | re.IGNORECASE)
    if cerca:
        limpo = cerca.group(1).strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find("{")
        fim = limpo.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            return json.loads(limpo[inicio : fim + 1])
        raise


def _tokens(texto: str) -> list[str]:
    stop = {
        "a",
        "o",
        "e",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "em",
        "no",
        "na",
        "um",
        "uma",
        "os",
        "as",
        "que",
        "com",
        "para",
        "por",
        "ao",
        "à",
        "se",
        "não",
        "nao",
        "meu",
        "minha",
        "alunos",
        "aluno",
        "aula",
        "sala",
    }
    words = re.findall(r"[A-Za-zÀ-ÿ]{4,}", (texto or "").lower())
    out = []
    seen = set()
    for w in words:
        if w in stop or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= 8:
            break
    return out


def _buscar_problemas_referencia(
    problema: str, contexto: str, limit: int | None = None
) -> list[dict]:
    if limit is None:
        limit = WIZARD_REF_LIMIT
    tokens = _tokens(f"{problema} {contexto}")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if tokens:
                clauses = []
                params: list = []
                for t in tokens:
                    like = f"%{t}%"
                    clauses.append(
                        "(desc_prob ILIKE %s OR razoes_prob ILIKE %s OR "
                        "categoria_prob ILIKE %s OR solucoes_prob ILIKE %s OR grupo_prob ILIKE %s)"
                    )
                    params.extend([like, like, like, like, like])
                where = " OR ".join(clauses)
                cur.execute(
                    f"""
                    SELECT id_prob, grupo_prob, categoria_prob, desc_prob,
                           razoes_prob, solucoes_prob
                    FROM public.ctdi_problemas_referencia
                    WHERE {where}
                    ORDER BY id_prob ASC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]

            cur.execute(
                """
                SELECT id_prob, grupo_prob, categoria_prob, desc_prob,
                       razoes_prob, solucoes_prob
                FROM public.ctdi_problemas_referencia
                ORDER BY id_prob ASC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def _parse_duracao_min(val: object, default: int = 10) -> int:
    try:
        n = int(float(val))
    except (TypeError, ValueError):
        return default
    return max(5, min(n, 180))


def _plano_from_db(
    metodologia: str,
    missao: str,
    problema: str,
    contexto: str,
) -> dict:
    """Monta plano a partir do banco estático (ganchos template se sem IA)."""
    base = get_metodologia_por_nome(metodologia)
    if not base or not base.get("cards"):
        return _plano_padrao(missao, [f"Etapa da metodologia {metodologia}"])
    cards = aplicar_ganchos(base, None, problema=problema, contexto=contexto)
    return _plano_padrao(
        missao,
        cards,
        contexto_execucao=base.get("contexto_execucao"),
        duracao_total_estimada_min=duracao_total_cards(cards),
    )


def _plano_padrao(
    missao: str,
    tarefas: list,
    *,
    contexto_execucao: str | None = None,
    duracao_total_estimada_min: int | None = None,
) -> dict:
    """Monta plano EduScrum. `tarefas` aceita strings ou dicts de passo didático (4–7)."""
    cores = ["#FDE68A", "#FDBA74", "#FCA5A5", "#A7F3D0", "#BFDBFE", "#DDD6FE", "#FBCFE8"]
    kanban = []
    passos_norm: list[dict] = []
    teve_duracao_explicita = False
    for i, t in enumerate(tarefas[:7]):
        if isinstance(t, dict):
            titulo = str(
                t.get("titulo_do_card")
                or t.get("titulo")
                or t.get("title")
                or ""
            ).strip()
            # Filtra placeholder do schema ("CONTINUE GERANDO...") se vier literal.
            if "CONTINUE GERANDO" in titulo.upper():
                continue
            objetivo = str(t.get("objetivo") or "").strip()
            mecanica = str(
                t.get("como_executar_detalhado")
                or t.get("mecanica_passo_a_passo")
                or t.get("descricao")
                or t.get("description")
                or ""
            ).strip()
            dica = str(t.get("dica_de_facilitacao") or "").strip()
            foco = str(t.get("foco_da_metodologia_escolhida") or "").strip()
            gancho = str(t.get("gancho_adaptacao") or "").strip()
            if t.get("duracao_minutos") is not None:
                teve_duracao_explicita = True
            duracao = _parse_duracao_min(t.get("duracao_minutos"), 10)
            if not titulo and mecanica:
                titulo = mecanica[:120]
            if not titulo:
                continue
            # `descricao` / `mecanica_passo_a_passo` espelham para UIs legadas.
            card = {
                "id": f"t{i + 1}",
                "titulo": titulo,
                "titulo_do_card": titulo,
                "coluna": "para_fazer",
                "cor": cores[i % len(cores)],
                "objetivo": objetivo,
                "como_executar_detalhado": mecanica,
                "mecanica_passo_a_passo": mecanica,
                "dica_de_facilitacao": dica,
                "foco_da_metodologia_escolhida": foco,
                "gancho_adaptacao": gancho,
                "duracao_minutos": duracao,
                "descricao": mecanica or objetivo,
            }
            kanban.append(card)
            passos_norm.append(
                {
                    "titulo_do_card": titulo,
                    "titulo": titulo,
                    "objetivo": objetivo,
                    "como_executar_detalhado": mecanica,
                    "mecanica_passo_a_passo": mecanica,
                    "dica_de_facilitacao": dica,
                    "foco_da_metodologia_escolhida": foco,
                    "gancho_adaptacao": gancho,
                    "duracao_minutos": duracao,
                }
            )
        else:
            titulo = str(t).strip()
            if not titulo:
                continue
            kanban.append(
                {
                    "id": f"t{i + 1}",
                    "titulo": titulo,
                    "coluna": "para_fazer",
                    "cor": cores[i % len(cores)],
                    "objetivo": "",
                    "mecanica_passo_a_passo": "",
                    "dica_de_facilitacao": "",
                    "foco_da_metodologia_escolhida": "",
                    "duracao_minutos": 10,
                    "descricao": "",
                }
            )
            passos_norm.append(
                {
                    "titulo": titulo,
                    "objetivo": "",
                    "mecanica_passo_a_passo": "",
                    "dica_de_facilitacao": "",
                    "foco_da_metodologia_escolhida": "",
                    "duracao_minutos": 10,
                }
            )

    # Sem duração explícita da IA: reparte 50 min (padrão de aula em sala).
    if kanban and not teve_duracao_explicita:
        base = 50 // len(kanban)
        resto = 50 % len(kanban)
        for i, c in enumerate(kanban):
            mins = max(5, base + (1 if i < resto else 0))
            c["duracao_minutos"] = mins
            if i < len(passos_norm):
                passos_norm[i]["duracao_minutos"] = mins

    soma_cards = sum(int(c.get("duracao_minutos") or 0) for c in kanban) or 50
    if duracao_total_estimada_min is not None:
        total = max(_parse_duracao_min(duracao_total_estimada_min, soma_cards), soma_cards)
    else:
        total = soma_cards
    ctx = (contexto_execucao or "").strip().lower()
    if ctx not in ("sala", "campo", "misto"):
        ctx = "campo" if total > 60 else "sala"

    # Timeline derivada dos cards (substitui Planejamento/Ação/Retrospectiva genéricos).
    timebox = [
        {
            "fase": c["titulo"][:80],
            "minutos": int(c.get("duracao_minutos") or 10),
            "descricao": (c.get("objetivo") or c.get("descricao") or "")[:160],
            "card_id": c.get("id"),
        }
        for c in kanban
    ]

    return {
        "missao": missao,
        "papeis": {
            "lider": "Líder — organiza o time e garante o foco na missão",
            "guardiao": "Guardião do Tempo — acompanha o progresso dos cards",
            "apresentador": "Apresentador — sintetiza e compartilha a entrega",
        },
        "contexto_execucao": ctx,
        "duracao_total_estimada_min": total,
        "dinamica_passo_a_passo": passos_norm,
        "tarefas_kanban": kanban,
        "timebox": timebox,
    }


def _fallback_payload(problema: str, contexto: str, refs: list[dict]) -> dict:
    ref = refs[0] if refs else None
    causa_base = (ref or {}).get("razoes_prob") or "Baixo engajamento e falta de propósito compartilhado."
    solucao = (ref or {}).get("solucoes_prob") or "Dinâmicas ativas e feedback rápido."
    categoria = (ref or {}).get("categoria_prob") or "Sala de aula"
    desc = (ref or {}).get("desc_prob") or problema

    causas = [
        {
            "titulo": "Causa estrutural",
            "descricao": str(causa_base)[:320],
            "origem": "base_referencia" if ref else "heuristica",
        },
        {
            "titulo": "Contexto da turma",
            "descricao": (
                f"No contexto «{contexto or 'sala de aula'}», o sintoma «{desc}» "
                f"se manifesta de forma recorrente e precisa de intervenção prática."
            )[:320],
            "origem": "contexto_professor",
        },
        {
            "titulo": "Lacuna de protagonismo",
            "descricao": (
                "Os estudantes não enxergam papel ativo na resolução do problema, "
                "o que reduz responsabilidade coletiva e aprendizagem significativa."
            ),
            "origem": "heuristica",
        },
    ]

    caminho_a = {
        "id": "A",
        "tipo_ranking": "encaixe_direto",
        "titulo": "Design Thinking Express na dor da turma",
        "metodologia": "Design Thinking Express",
        "quadrante": "criativas",
        "resumo": (
            f"Encaixe direto: empatizar, idear e prototipar uma resposta rápida "
            f"ao desafio «{categoria}» em um ciclo de aula."
        ),
        "por_que_usar": (
            "Quando o problema é concreto e a turma precisa gerar soluções próprias, "
            "o Design Thinking Express acelera empatia → ideia → protótipo sem perder foco."
        ),
        "dinamica_sala": (
            "Times mapeiam a dor em 5 min, geram 5 ideias, escolhem 1 e prototipam "
            "um micro-roteiro de intervenção; fecham com pitch de 60s."
        ),
        "hipotese_teste": (
            f"Se aplicarmos Design Thinking Express a «{problema[:120]}», "
            f"os alunos aprenderão a transformar empatia em protótipo acionável "
            f"em um timebox de 50 minutos."
        ),
        "inspiracao_caso": None,
        "ancoragem_de_para": None,
        "plano_eduscrum": _plano_from_db(
            "Design Thinking Express",
            f"Missão: prototipar uma resposta ativa a «{problema[:80]}».",
            problema,
            contexto,
        ),
    }

    caminho_b = {
        "id": "B",
        "tipo_ranking": "encaixe_alternativo",
        "titulo": "Diagnóstico Coletivo antes da ação",
        "metodologia": "Diagnóstico Coletivo",
        "quadrante": "analiticas",
        "resumo": (
            "Mudança de dinâmica: primeiro evidência coletiva, depois decisão "
            f"de intervenção. Âncora: {str(solucao)[:100]}."
        ),
        "por_que_usar": (
            "Quando há sintomas difusos, o Diagnóstico Coletivo (quadrante analítico) "
            "evita saltar para soluções e alinha a turma em fatos compartilhados."
        ),
        "dinamica_sala": (
            "Cada time coleta 3 sinais observáveis, cruza no mural coletivo, "
            "prioriza 1 causa e define um micro-teste para a próxima ação."
        ),
        "hipotese_teste": (
            f"Se rodarmos Diagnóstico Coletivo sobre «{problema[:120]}», "
            f"os alunos aprenderão a decidir com evidência compartilhada "
            f"antes de propor a intervenção."
        ),
        "inspiracao_caso": None,
        "ancoragem_de_para": None,
        "plano_eduscrum": _plano_from_db(
            "Diagnóstico Coletivo",
            f"Missão: diagnosticar coletivamente «{problema[:80]}».",
            problema,
            contexto,
        ),
    }

    caminho_c = {
        "id": "C",
        "tipo_ranking": "adaptacao_hibrida",
        "titulo": "Elevator Pitch com inspiração de pitch público",
        "metodologia": "Elevator Pitch",
        "quadrante": "ageis",
        "resumo": (
            "Híbrido: fôrma Ágil (Elevator Pitch) + prática de síntese pública "
            "para forçar clareza sobre o problema e a solução proposta."
        ),
        "por_que_usar": (
            "Quando a turma precisa comunicar a proposta com precisão e tempo curto, "
            "o Elevator Pitch treina síntese, persuasão e foco na aprendizagem."
        ),
        "dinamica_sala": (
            "Times preparam pitch de 60–90s (problema → insight → proposta → pedido), "
            "apresentam em rodada rápida e recebem feedback com rubrica curta."
        ),
        "hipotese_teste": (
            f"Se os alunos sintetizarem «{problema[:100]}» em Elevator Pitch, "
            f"aprenderão a comunicar a proposta com clareza e a validar se o "
            f"público entende o valor em menos de 90 segundos."
        ),
        "inspiracao_caso": (
            "Formatos públicos de pitch curto em feiras de inovação escolar e "
            "hackathons educacionais, onde times defendem soluções em 1 minuto."
        ),
        "ancoragem_de_para": (
            "De: pitch de 60s em feira/hackathon educacional (Mundo Real) / "
            "Para: Metodologia Ágil Elevator Pitch (Nossa Teoria)"
        ),
        "plano_eduscrum": _plano_from_db(
            "Elevator Pitch",
            f"Missão: pitchar a solução para «{problema[:80]}».",
            problema,
            contexto,
        ),
    }

    return {
        "resumo_analise": (
            f"O desafio «{desc[:160]}» pede intervenção ativa: há sintomas de "
            f"«{categoria}» que se resolvem melhor com metodologias Inov-Ativas "
            f"ancoradas em evidência e entrega em aula."
        ),
        "causas_raiz": causas,
        "caminhos": [caminho_a, caminho_b, caminho_c],
        "hipotese_teste": None,
        "plano_eduscrum": None,
        "referencial": {
            "id_prob": (ref or {}).get("id_prob"),
            "grupo_prob": (ref or {}).get("grupo_prob"),
            "categoria_prob": (ref or {}).get("categoria_prob"),
            "desc_prob": (ref or {}).get("desc_prob"),
            "matches": len(refs),
        },
    }


_IDS_RANKING = ("A", "B", "C")
_TIPOS_RANKING = ("encaixe_direto", "encaixe_alternativo", "adaptacao_hibrida")


def _normalizar_payload(raw: dict, problema: str, contexto: str, refs: list[dict]) -> dict:
    base = _fallback_payload(problema, contexto, refs)
    if not isinstance(raw, dict):
        return base

    resumo = raw.get("resumo_analise")
    if isinstance(resumo, str) and resumo.strip():
        base["resumo_analise"] = resumo.strip()[:600]

    causas = raw.get("causas_raiz") or base["causas_raiz"]
    if isinstance(causas, list) and causas:
        base["causas_raiz"] = causas[:3]

    caminhos_in = raw.get("caminhos") or []
    caminhos_out = []
    for i, c in enumerate(caminhos_in[:3]):
        if not isinstance(c, dict):
            continue
        fallback = base["caminhos"][i] if i < len(base["caminhos"]) else base["caminhos"][0]
        plano = c.get("plano_eduscrum") or fallback["plano_eduscrum"]
        if not isinstance(plano, dict):
            plano = fallback["plano_eduscrum"]
        # Preferir passos temáticos (com foco_da_metodologia_escolhida); viram cards do Kanban.
        passos = plano.get("dinamica_passo_a_passo") or c.get("dinamica_passo_a_passo")
        tarefas = (
            passos
            if isinstance(passos, list) and passos
            else plano.get("tarefas_kanban") or fallback["plano_eduscrum"]["tarefas_kanban"]
        )
        missao = plano.get("missao") or fallback["plano_eduscrum"]["missao"]
        papeis = plano.get("papeis") if isinstance(plano.get("papeis"), dict) else None
        if isinstance(tarefas, list) and tarefas:
            plano = _plano_padrao(
                missao,
                tarefas,
                contexto_execucao=plano.get("contexto_execucao")
                or c.get("contexto_execucao"),
                duracao_total_estimada_min=plano.get("duracao_total_estimada_min")
                or c.get("duracao_total_estimada_min"),
            )
            if papeis:
                plano["papeis"] = papeis
        else:
            plano = fallback["plano_eduscrum"]

        caminhos_out.append(
            {
                "id": str(c.get("id") or _IDS_RANKING[i]),
                "tipo_ranking": c.get("tipo_ranking") or _TIPOS_RANKING[i],
                "titulo": c.get("titulo") or fallback["titulo"],
                "metodologia": _normalizar_nome_metodologia(
                    c.get("metodologia") or fallback.get("metodologia")
                ),
                "quadrante": c.get("quadrante") or fallback.get("quadrante"),
                "resumo": c.get("resumo") or fallback["resumo"],
                "por_que_usar": c.get("por_que_usar") or fallback.get("por_que_usar"),
                "dinamica_sala": c.get("dinamica_sala") or fallback.get("dinamica_sala"),
                "hipotese_teste": c.get("hipotese_teste") or fallback["hipotese_teste"],
                "inspiracao_caso": c.get("inspiracao_caso")
                if c.get("inspiracao_caso") is not None
                else fallback.get("inspiracao_caso"),
                "ancoragem_de_para": c.get("ancoragem_de_para")
                if c.get("ancoragem_de_para") is not None
                else fallback.get("ancoragem_de_para"),
                "plano_eduscrum": plano,
            }
        )

    if len(caminhos_out) < 3:
        caminhos_out = base["caminhos"]

    base["caminhos"] = caminhos_out
    return base


def _categoria_para_quadrante(categoria: str | None) -> str:
    cat = str(categoria or "").strip().upper()
    if cat.startswith("ÁG") or cat.startswith("AG"):
        return "ageis"
    if cat.startswith("CRI"):
        return "criativas"
    if cat.startswith("IMER"):
        return "imersivas"
    if cat.startswith("ANAL"):
        return "analiticas"
    return "criativas"


def _injetar_gancho_primeiro_card(cards: list, gancho: str) -> list:
    """Injeta o gancho_adaptacao no 1º card (deepcopy já feito pelo caller)."""
    if not cards or not gancho:
        return cards
    primeiro = cards[0]
    mec = str(
        primeiro.get("mecanica_passo_a_passo")
        or primeiro.get("como_executar_detalhado")
        or ""
    ).strip()
    injected = f"**💡 Adaptando para sua aula:** {gancho}\n\n{mec}".strip()
    primeiro["mecanica_passo_a_passo"] = injected
    primeiro["como_executar_detalhado"] = injected
    primeiro["gancho_adaptacao"] = gancho
    return cards


def _montar_caminho_hibrido(
    letra: str,
    tipo_ranking: str,
    opt: dict,
    *,
    problema: str,
    contexto: str,
) -> dict:
    """Costura: id_metodologia + gancho LLM → caminho completo com cards do DB."""
    mid = resolve_metodologia_id(opt.get("id_metodologia"))
    db_data = get_metodologia(mid) if mid else None
    if not db_data or not db_data.get("cards"):
        print(
            f"[wizard] metodologia ausente ({opt.get('id_metodologia')!r}) "
            f"— fallback {_DEFAULT_METODOLOGIA_ID}",
            file=sys.stderr,
        )
        db_data = get_metodologia(_DEFAULT_METODOLOGIA_ID) or {}

    gancho = str(opt.get("gancho_adaptacao") or "").strip()
    cards = copy.deepcopy(db_data.get("cards") or [])
    cards = _injetar_gancho_primeiro_card(cards, gancho)

    nome = str(db_data.get("nome") or "Metodologia Inov-Ativa").strip()
    categoria = str(db_data.get("categoria") or "").strip()
    quadrante = _categoria_para_quadrante(categoria)
    trecho = " ".join(problema.split())[:100]
    gancho_resumo = gancho[:360] if gancho else (
        f"Aplicação de {nome} ao desafio «{trecho}»."
    )

    missao = f"Missão: aplicar {nome} a «{trecho}»."
    plano = _plano_padrao(
        missao,
        cards,
        contexto_execucao=db_data.get("contexto_execucao"),
        duracao_total_estimada_min=duracao_total_cards(cards),
    )
    plano["fonte_cards"] = "metodologias_db"
    plano["id_metodologia"] = mid or _DEFAULT_METODOLOGIA_ID

    caminho: dict = {
        "id": letra,
        "tipo_ranking": tipo_ranking,
        "titulo": f"{nome} no desafio da turma",
        "metodologia": nome,
        "quadrante": quadrante,
        "id_metodologia": mid or _DEFAULT_METODOLOGIA_ID,
        "resumo": gancho_resumo,
        "por_que_usar": gancho_resumo,
        "dinamica_sala": gancho_resumo,
        "hipotese_teste": (
            f"Se aplicarmos {nome} a «{trecho}», "
            f"os alunos aprenderão com a mecânica desta metodologia "
            f"ancorada no contexto «{contexto or 'sala de aula'}»."
        ),
        "inspiracao_caso": None,
        "ancoragem_de_para": None,
        "plano_eduscrum": plano,
        # Espelho compacto pedido na arquitetura híbrida (debug / futuros clientes).
        "nome": nome,
        "categoria": categoria,
        "cards": cards,
    }
    if tipo_ranking == "adaptacao_hibrida":
        caminho["inspiracao_caso"] = gancho_resumo[:220]
        caminho["ancoragem_de_para"] = (
            f"[De: desafio do professor] -> [Para: {nome} ({mid or _DEFAULT_METODOLOGIA_ID})]"
        )
    return caminho


def _stitch_ranking_hibrido(
    raw: dict,
    problema: str,
    contexto: str,
    refs: list[dict],
) -> dict:
    """
    Costura o JSON curto do LLM (A/B/C) com cards imutáveis do METODOLOGIAS_DB.
    Mantém o contrato do frontend: resumo, causas_raiz, caminhos[].plano_eduscrum.
    """
    base = _fallback_payload(problema, contexto, refs)
    if not isinstance(raw, dict):
        return base

    # Formato legado (caminhos[]) — ainda normaliza se aparecer.
    if isinstance(raw.get("caminhos"), list) and raw["caminhos"]:
        return _normalizar_payload(raw, problema, contexto, refs)

    caminhos_out = []
    for i, letra in enumerate(_IDS_RANKING):
        opt = raw.get(letra)
        if not isinstance(opt, dict):
            continue
        caminhos_out.append(
            _montar_caminho_hibrido(
                letra,
                _TIPOS_RANKING[i],
                opt,
                problema=problema,
                contexto=contexto,
            )
        )

    if len(caminhos_out) < 3:
        raise ValueError(
            f"Ranking híbrido incompleto: esperava A/B/C, veio {list(raw.keys())}"
        )

    # resumo/causas: LLM híbrido não envia — heurística a partir do problema/refs.
    trecho = " ".join(problema.split())[:160]
    base["resumo_analise"] = (
        f"Ranking híbrido para «{trecho}»: três metodologias Inov-Ativas "
        f"roteadas pela IA e costuradas com mecânicas estáticas do banco."
    )[:600]
    base["caminhos"] = caminhos_out
    return base


@wizard_bp.post("/api/wizard/estruturar")
def estruturar_problema():
    """Recebe o problema do professor e devolve JSON para as etapas 2–4.

    Freemium local: 1 crédito IA por geração bem-sucedida via Bedrock.
    Upgrade/pagamentos ficam no ActionHub (webhooks — passo futuro).
    """
    user = session.get("user") or {}
    id_clie = user.get("id_clie")
    if not id_clie:
        return jsonify({"error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    problema = str(data.get("problema") or "").strip()
    contexto = str(data.get("contexto") or data.get("localizacao") or "").strip()

    if len(problema) < 12:
        return jsonify({"error": "Descreva o problema com pelo menos algumas frases."}), 400

    try:
        saldo = get_creditos_ia(int(id_clie))
    except Exception as exc:
        print(f"[wizard] créditos: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao consultar créditos de uso."}), 500

    if saldo <= 0:
        return (
            jsonify(
                {
                    "erro": "Limite de uso gratuito atingido.",
                    "code": "INSUFFICIENT_CREDITS",
                }
            ),
            403,
        )

    try:
        refs = _buscar_problemas_referencia(problema, contexto)
    except Exception as exc:
        print(f"[wizard] DB error: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao consultar a base de problemas."}), 500

    def _clip(val: object, n: int = 180) -> str:
        s = " ".join(str(val or "").split())
        return s if len(s) <= n else s[: n - 1] + "…"

    bloco_ref = "\n".join(
        [
            f"- [{r['id_prob']}] {_clip(r['grupo_prob'], 40)} › {_clip(r['categoria_prob'], 40)}: "
            f"{_clip(r['desc_prob'])} | Causas: {_clip(r['razoes_prob'])} | "
            f"Soluções: {_clip(r['solucoes_prob'])}"
            for r in refs[:WIZARD_REF_LIMIT]
        ]
    ) or "Sem matches fortes — use heurística pedagógica sólida."

    system_prompt = build_estruturar_system_prompt(bloco_ref)

    user_content = (
        f"PROBLEMA DO PROFESSOR:\n{problema}\n\n"
        f"LOCALIZAÇÃO / CONTEXTO:\n{contexto or 'Não informado'}\n\n"
        f"id_clie: {id_clie}"
    )

    usou_fallback = False
    json_prefill = "{"
    model_id = WIZARD_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    try:
        bedrock = _get_bedrock_runtime_client()
        # Uma única chamada curta: roteador A/B/C + ganchos (cards vêm do DB).
        raw = _invoke_estruturar_bedrock(
            bedrock=bedrock,
            model_id=model_id,
            system_prompt=system_prompt,
            user_content=user_content,
            max_tokens=BEDROCK_MAX_TOKENS,
            json_prefill=json_prefill,
        )
        payload = _stitch_ranking_hibrido(raw, problema, contexto, refs)
    except Exception as exc:
        print(f"[wizard] Bedrock/fallback: {exc}", file=sys.stderr)
        payload = _fallback_payload(problema, contexto, refs)
        usou_fallback = True

    creditos_restantes = saldo
    # Consome crédito somente quando a IA respondeu com sucesso (não no fallback local)
    if not usou_fallback:
        try:
            novo = consumir_credito_ia(int(id_clie))
            if novo is not None:
                creditos_restantes = novo
                if isinstance(session.get("user"), dict):
                    session["user"]["creditos_ia"] = novo
                    session.modified = True
            else:
                print(
                    f"[wizard] aviso: IA ok mas não foi possível debitar crédito id_clie={id_clie}",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"[wizard] erro ao debitar crédito: {exc}", file=sys.stderr)

    return jsonify(
        {
            "status": "success",
            "problema": problema,
            "contexto": contexto,
            "resumo_analise": payload.get("resumo_analise"),
            "causas_raiz": payload["causas_raiz"],
            "caminhos": payload["caminhos"],
            "hipotese_teste": payload.get("hipotese_teste"),
            "plano_eduscrum": payload.get("plano_eduscrum"),
            "referencial": payload.get("referencial"),
            "fallback": usou_fallback,
            "creditos_ia": creditos_restantes,
        }
    )


@wizard_bp.post("/api/wizard/selecionar-caminho")
def selecionar_caminho():
    """Consolida hipótese + plano a partir do caminho escolhido (alimenta etapas 3–4)."""
    data = request.get_json(silent=True) or {}
    caminho = data.get("caminho") or {}
    if not isinstance(caminho, dict) or not caminho.get("hipotese_teste"):
        return jsonify({"error": "Caminho inválido."}), 400

    plano = caminho.get("plano_eduscrum")
    if not isinstance(plano, dict):
        return jsonify({"error": "Plano EduScrum ausente no caminho."}), 400

    return jsonify(
        {
            "status": "success",
            "hipotese_teste": caminho.get("hipotese_teste"),
            "plano_eduscrum": plano,
            "caminho_id": caminho.get("id"),
            "caminho_titulo": caminho.get("titulo"),
        }
    )
