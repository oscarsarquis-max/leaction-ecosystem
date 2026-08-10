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
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

import boto3
from botocore.config import Config
from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from core.catalogo_metodologias_dia import (
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
    ETIQUETA_DEDUTIVAS,
    ETIQUETA_INDUTIVAS,
    etiqueta_publica,
    ids_catalogo_por_etiqueta,
    resolver_entrada_catalogo,
)
from core.tom_pedagogico import (
    LIMITE_GANCHO,
    LIMITE_HIPOTESE,
    completar_frase,
    dinamica_em_sala,
    justificar_para_professor,
)
from core.metodologias_db import (
    aplicar_ganchos,
    duracao_total_cards,
    get_metodologia,
    get_metodologia_por_nome,
    resolve_metodologia_id,
)
from services.methodology_service import get_dinamica_by_id
from db import consumir_credito_ia, get_conn, get_creditos_ia
from prompts.inov_ativas import LISTA_FLAT, build_estruturar_system_prompt
from wizard_qualidade import (
    aplicar_barreira_final_payload,
    avaliar_qualidade,
    causas_somente_do_relato,
    contar_causas_ia,
    contem_termo_do_relato,
    contexto_seguro_para_ui,
    corpus_textos_de_refs,
    estimate_tokens,
    extrair_trecho_relato,
    forcar_ancoragem_payload,
    frase_tema_do_relato,
    jaccard_words,
    relato_insufficiente,
    sanitizar_causas_ia,
    similaridade_texto,
    texto_professor_limpo,
    vaza_contra_corpus,
    vinculo_minimo_com_relato,
)


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
# Arquitetura híbrida: 1 chamada (roteador A/B/C + ganchos). Cards vêm do DB.
# Qualidade: Sonnet (padrão). Haiku/30s degradou a análise em prod — não repetir.
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "4096"))
WIZARD_REF_LIMIT = int(os.environ.get("WIZARD_REF_LIMIT", "2"))
# Vazio = BEDROCK_MODEL_ID (Sonnet). Só force Haiku via env se for teste explícito.
WIZARD_BEDROCK_MODEL_ID = os.environ.get("WIZARD_BEDROCK_MODEL_ID", "").strip()
# Teto abaixo do idle_timeout do ALB (60s) para evitar 504; fallback só se estourar.
WIZARD_BEDROCK_READ_TIMEOUT = int(os.environ.get("WIZARD_BEDROCK_READ_TIMEOUT", "50"))
WIZARD_TOTAL_BUDGET_SEC = float(os.environ.get("WIZARD_TOTAL_BUDGET_SEC", "55"))
# Retry de qualidade ligado (era o comportamento estável pré-SLA-30s).
WIZARD_RETRY_ENABLED = os.environ.get("WIZARD_RETRY_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
WIZARD_RETRY_MIN_REMAINING_SEC = float(
    os.environ.get("WIZARD_RETRY_MIN_REMAINING_SEC", "22")
)
# Fallback canônico no catálogo das 39 (não inventar fora da lista)
_DEFAULT_METODOLOGIA_ID = "criativa_narrativas_transmidia"


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
    read_timeout = max(15, min(int(WIZARD_BEDROCK_READ_TIMEOUT), 55))
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        # Qualidade Sonnet com teto < ALB 60s; se estourar → pad (já corrigido).
        config=Config(
            connect_timeout=8,
            read_timeout=read_timeout,
            retries={"max_attempts": 1},
        ),
    )


def _invoke_estruturar_bedrock_deadline(
    *,
    bedrock,
    model_id: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int,
    json_prefill: str,
    deadline_sec: float,
) -> dict:
    """Chama Bedrock com teto de parede; TimeoutError se estourar o SLA."""
    remaining = max(1.0, float(deadline_sec))
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(
            _invoke_estruturar_bedrock,
            bedrock=bedrock,
            model_id=model_id,
            system_prompt=system_prompt,
            user_content=user_content,
            max_tokens=max_tokens,
            json_prefill=json_prefill,
        )
        try:
            return fut.result(timeout=remaining)
        except FuturesTimeout as exc:
            fut.cancel()
            raise TimeoutError(
                f"Bedrock ultrapassou o SLA de {remaining:.0f}s"
            ) from exc


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
    """Busca âncoras de estilo ranqueadas por nº de tokens batendo — nunca por id_prob."""
    if limit is None:
        limit = WIZARD_REF_LIMIT
    tokens = _tokens(f"{problema} {contexto}")
    if not tokens:
        return []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            clauses = []
            params: list = []
            score_parts = []
            for t in tokens:
                like = f"%{t}%"
                clauses.append(
                    "(desc_prob ILIKE %s OR razoes_prob ILIKE %s OR "
                    "categoria_prob ILIKE %s OR solucoes_prob ILIKE %s OR grupo_prob ILIKE %s)"
                )
                params.extend([like, like, like, like, like])
                score_parts.append(
                    "(CASE WHEN desc_prob ILIKE %s OR razoes_prob ILIKE %s OR "
                    "categoria_prob ILIKE %s OR solucoes_prob ILIKE %s OR grupo_prob ILIKE %s "
                    "THEN 1 ELSE 0 END)"
                )
                params.extend([like, like, like, like, like])
            where = " OR ".join(clauses)
            score_expr = " + ".join(score_parts)
            cur.execute(
                f"""
                SELECT id_prob, grupo_prob, categoria_prob, desc_prob,
                       razoes_prob, solucoes_prob,
                       ({score_expr}) AS match_score
                FROM public.ctdi_problemas_referencia
                WHERE {where}
                ORDER BY match_score DESC, id_prob ASC
                LIMIT %s
                """,
                (*params, limit),
            )
            rows = cur.fetchall()
            # Exige pelo menos 2 tokens batendo para não ancorar em "aula"/"aluno" genérico
            out = []
            for r in rows:
                score = int(r.get("match_score") or 0)
                if score < 2 and len(tokens) >= 2:
                    continue
                out.append(dict(r))
            return out[:limit]


_CORPUS_REF_CACHE: list[str] | None = None


def _carregar_corpus_referencia_completo() -> list[str]:
    """Tabela inteira de ctdi_problemas_referencia — barreira final (sem custo de IA)."""
    global _CORPUS_REF_CACHE
    if _CORPUS_REF_CACHE is not None:
        return _CORPUS_REF_CACHE
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT desc_prob, razoes_prob, solucoes_prob
                    FROM public.ctdi_problemas_referencia
                    """
                )
                rows = cur.fetchall() or []
        _CORPUS_REF_CACHE = corpus_textos_de_refs([dict(r) for r in rows])
        print(
            f"[wizard] corpus_ref carregado n={len(_CORPUS_REF_CACHE)}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"[wizard] corpus_ref indisponível: {exc}", file=sys.stderr)
        _CORPUS_REF_CACHE = []
    return _CORPUS_REF_CACHE


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


_IDS_RANKING = ("A", "B", "C")
_TIPOS_RANKING = ("encaixe_direto", "encaixe_alternativo", "adaptacao_hibrida")


def _fallback_payload(
    problema: str,
    contexto: str,
    refs: list[dict],
    corpus_refs: list[str] | None = None,
) -> dict:
    ref = refs[0] if refs else None
    trecho = extrair_trecho_relato(problema)
    corpus = corpus_refs if corpus_refs is not None else _carregar_corpus_referencia_completo()
    causas = causas_somente_do_relato(problema, contexto, corpus)

    # Fallback local: 3 famílias distintas, IDs fora do trio habitual da IA
    fb_ids = [
        _pick_metodologia_diversa(set(), preferred_id=None, slot=i, seed=problema or contexto or "")
        for i in range(3)
    ]
    # Garante unicidade mesmo se o seed colapsar
    used_fb: set[str] = set()
    fb_ids_unique: list[str] = []
    for i, mid in enumerate(fb_ids):
        mid = _pick_metodologia_diversa(
            used_fb, preferred_id=mid, slot=i, seed=problema or contexto or ""
        )
        used_fb.add(mid)
        fb_ids_unique.append(mid)

    caminhos_fb = []
    for i, mid in enumerate(fb_ids_unique):
        caminhos_fb.append(
            _montar_caminho_hibrido(
                _IDS_RANKING[i],
                _TIPOS_RANKING[i],
                {
                    "id_metodologia": mid,
                    "gancho_adaptacao": (
                        f"Adaptação de catálogo ao trecho «{trecho}»."
                    ),
                    "hipotese_teste": "",
                    "trecho_relato_usado": trecho,
                },
                problema=problema,
                contexto=contexto,
                trecho_relato=trecho,
                refs_no_prompt=refs,
                forced_mid=mid,
            )
        )
    caminho_a, caminho_b, caminho_c = caminhos_fb

    return {
        "resumo_analise": (
            f"Pelo que você descreveu, a turma se beneficia de uma aprendizagem mais ativa, "
            f"com prática mediada e evidência clara do que foi aprendido. "
            f"Abaixo estão três caminhos metodológicos para a sua aula — "
            f"escolha o que melhor combina com o seu objetivo e com o tempo disponível."
        ),
        "causas_raiz": causas,
        "caminhos": [caminho_a, caminho_b, caminho_c],
        "hipotese_teste": None,
        "plano_eduscrum": None,
        "trecho_relato_usado": trecho,
        "referencial": {
            "id_prob": (ref or {}).get("id_prob"),
            "grupo_prob": (ref or {}).get("grupo_prob"),
            "categoria_prob": (ref or {}).get("categoria_prob"),
            # desc_prob NÃO vai para a UI como sintoma do professor
            "matches": len(refs),
        },
        "qualidade": {
            "vinculo_relato_ok": True,
            "possivel_vazamento": False,
            "fonte": "fallback_local",
        },
    }


def _normalizar_payload(
    raw: dict,
    problema: str,
    contexto: str,
    refs: list[dict],
    corpus_refs: list[str] | None = None,
) -> dict:
    corpus = corpus_refs if corpus_refs is not None else _carregar_corpus_referencia_completo()
    base = _fallback_payload(problema, contexto, refs, corpus)
    if not isinstance(raw, dict):
        return base

    resumo = raw.get("resumo_analise")
    if isinstance(resumo, str) and resumo.strip():
        base["resumo_analise"] = resumo.strip()

    # NUNCA aceitar causas_raiz cruas do modelo/legado sem sanitizar
    base["causas_raiz"] = sanitizar_causas_ia(
        raw.get("causas") or raw.get("causas_raiz"),
        problema=problema,
        contexto=contexto,
        refs_no_prompt=refs,
        corpus_refs=corpus,
    )

    # Preferir costura híbrida (catálogo) em vez de aceitar por_que_usar da IA
    # (que frequentemente copia o texto do desafio).
    caminhos_in = raw.get("caminhos") or []
    caminhos_out = []
    trecho = extrair_trecho_relato(problema)
    used_mids: set[str] = set()
    for i, c in enumerate(caminhos_in[:3]):
        if not isinstance(c, dict):
            continue
        preferred = _resolve_catalog_id(
            c.get("id_metodologia") or c.get("metodologia")
        )
        mid = _pick_metodologia_diversa(
            used_mids,
            preferred_id=preferred,
            slot=i,
            seed=problema or contexto or "",
        )
        used_mids.add(mid)
        gancho = str(
            c.get("gancho_adaptacao")
            or c.get("resumo")
            or c.get("por_que_usar")
            or ""
        ).strip()
        caminhos_out.append(
            _montar_caminho_hibrido(
                str(c.get("id") or _IDS_RANKING[i]),
                c.get("tipo_ranking") or _TIPOS_RANKING[i],
                {
                    "id_metodologia": mid,
                    "gancho_adaptacao": gancho,
                    "hipotese_teste": c.get("hipotese_teste") or "",
                    "trecho_relato_usado": trecho,
                },
                problema=problema,
                contexto=contexto,
                trecho_relato=trecho,
                refs_no_prompt=refs,
                forced_mid=mid,
            )
        )

    if len(caminhos_out) < 3:
        caminhos_out = base["caminhos"]

    base["caminhos"] = caminhos_out
    base["trecho_relato_usado"] = trecho
    return forcar_ancoragem_payload(
        base, problema=problema, contexto=contexto, corpus_refs=corpus
    )


def _categoria_para_quadrante(categoria: str | None) -> str:
    """Rótulo público (mesma reformulação do Dia a Dia)."""
    return etiqueta_publica(categoria)


def _mecanica_curta_catalogo(db_data: dict) -> str:
    focos: list[str] = []
    for card in db_data.get("cards") or []:
        if not isinstance(card, dict):
            continue
        f = str(card.get("foco_da_metodologia_escolhida") or "").strip()
        if f and f not in focos:
            focos.append(f)
        if len(focos) >= 2:
            break
    if focos:
        return "; ".join(focos)
    desc = str(db_data.get("descricao_curta") or "").strip()
    return desc or "prática ativa, mediação clara e evidência de aprendizagem"


def _por_que_usar_do_catalogo(
    db_data: dict,
    *,
    etiqueta: str | None = None,
    gancho: str = "",
    trecho: str = "",
) -> str:
    """Justificativa completa para o professor — sem cortar a ideia no meio."""
    nome = str(db_data.get("nome") or "esta dinâmica").strip()
    familia = etiqueta or etiqueta_publica(
        db_data.get("etiqueta") or db_data.get("categoria")
    )
    adapt = str(gancho or "").strip()
    # Evita colar o desafio inteiro como justificativa
    if adapt and trecho and similaridade_texto(adapt, trecho) >= 0.72:
        adapt = ""
    return justificar_para_professor(
        nome=nome,
        etiqueta=familia,
        mecanica=_mecanica_curta_catalogo(db_data),
        gancho=adapt,
        trecho=str(trecho or "").strip(),
    )


def _dinamica_sala_do_catalogo(db_data: dict) -> str:
    """Como conduzir em sala — texto completo, linguagem pedagógica."""
    nome = str(db_data.get("nome") or "a dinâmica").strip()
    cards = db_data.get("cards") or []
    if not cards or not isinstance(cards[0], dict):
        return dinamica_em_sala(
            nome=nome,
            descricao=str(db_data.get("descricao_curta") or "").strip(),
        )
    c0 = cards[0]
    obj = str(c0.get("objetivo") or "").strip()
    mec = str(
        c0.get("mecanica_passo_a_passo") or c0.get("como_executar_detalhado") or ""
    ).strip()
    # Remove eventual gancho já injetado em reprocessamentos
    mec = re.sub(
        r"(?is)^\*\*💡\s*Adaptando para sua aula:\*\*[^\n]*\n+",
        "",
        mec,
    ).strip()
    return dinamica_em_sala(nome=nome, objetivo=obj, mecanica=mec)


# Fallbacks A/B/C — preferir IDs com mecânica em METODOLOGIAS_DB
_FALLBACK_IDS_DIVERSOS = (
    "criativa_narrativas_transmidia",
    "analitica_learning_analytics",
    "agil_minute_paper",
)

_FAMILY_ETIQUETAS = (
    ETIQUETA_INDUTIVAS,
    ETIQUETA_DEDUTIVAS,
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
)

# Trio habitual da IA — rotacionamos dentro da mesma família na maioria dos casos
_OVERUSED_IDS = frozenset(
    {
        "criativa_design_thinking_express",
        "analitica_diagnostico_coletivo",
        "agil_elevator_pitch",
    }
)


def _resolve_catalog_id(nome_ou_id: str | None) -> str | None:
    """Resolve para id canônico das 39 (nunca inventa fora do catálogo)."""
    entrada = resolver_entrada_catalogo(nome_ou_id)
    if entrada:
        return entrada["id"]
    # legado: id do DB de 16 que ainda mapeia no catálogo via alias/id_db
    mid_db = resolve_metodologia_id(nome_ou_id)
    if mid_db:
        entrada = resolver_entrada_catalogo(mid_db)
        if entrada:
            return entrada["id"]
    return None


def _familia_de(mid: str | None) -> str:
    """Família pública (etiqueta) do id no catálogo das 39."""
    entrada = resolver_entrada_catalogo(mid)
    if entrada:
        return str(entrada.get("etiqueta") or "")
    return ""


def _ids_da_familia(etiqueta: str) -> list[str]:
    return ids_catalogo_por_etiqueta(etiqueta)


def _pick_metodologia_diversa(
    used: set[str],
    *,
    preferred_id: str | None = None,
    slot: int = 0,
    seed: str = "",
    exclude_ids: set[str] | None = None,
) -> str:
    """Escolhe entre as 39: IDs distintos + famílias distintas; rotaciona na família."""
    blocked = {str(x) for x in (exclude_ids or set()) if x}
    preferred = _resolve_catalog_id(preferred_id)
    if preferred and preferred in blocked:
        preferred = None
    used_families = {_familia_de(m) for m in used if _familia_de(m)}
    pref_fam = _familia_de(preferred) if preferred else ""
    rot = abs(hash((seed or "", slot))) if seed else slot

    if (
        preferred
        and preferred not in used
        and preferred not in blocked
        and (not pref_fam or pref_fam not in used_families)
    ):
        if preferred in _OVERUSED_IDS and rot % 3 != 0 and pref_fam:
            alts = [
                m
                for m in _ids_da_familia(pref_fam)
                if m not in used and m not in blocked and m not in _OVERUSED_IDS
            ]
            if alts:
                return alts[rot % len(alts)]
        return preferred

    ordered = [_FAMILY_ETIQUETAS[slot % len(_FAMILY_ETIQUETAS)]] + [
        f for i, f in enumerate(_FAMILY_ETIQUETAS) if i != slot % len(_FAMILY_ETIQUETAS)
    ]

    for etq in ordered:
        if etq in used_families:
            continue
        candidatos = [
            m for m in _ids_da_familia(etq) if m not in used and m not in blocked
        ]
        if candidatos:
            preferidos = [m for m in candidatos if m not in _OVERUSED_IDS] or candidatos
            return preferidos[rot % len(preferidos)]

    # Qualquer uma das 39 ainda livre
    from core.catalogo_metodologias_dia import entradas_catalogo_dia

    livres = [
        e["id"]
        for e in entradas_catalogo_dia()
        if e["id"] not in used and e["id"] not in blocked
    ]
    if livres:
        return livres[rot % len(livres)]
    # Último recurso: ignora bloqueio escolar só se o catálogo inteiro estiver vazio
    return _FALLBACK_IDS_DIVERSOS[slot % len(_FALLBACK_IDS_DIVERSOS)]


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


def _sinais_complexidade_projeto(problema: str, contexto: str = "") -> dict:
    """Lê o relato do professor e estima complexidade pedagógica do projeto."""
    blob = f"{problema or ''} {contexto or ''}".lower()
    interdisciplinar = bool(
        re.search(
            r"interdiscipl|matem[aá]tica|estat[ií]stica|sociologia|geografia|"
            r"l[ií]ngua\s+portuguesa|hist[oó]ria|ci[eê]ncias|v[aá]rias\s+disciplinas",
            blob,
        )
    )
    multi_aula = bool(
        re.search(
            r"projeto|semanas?|meses?|cronograma|sequ[eê]ncia|ciclo|"
            r"v[aá]rias\s+aulas|plurais?\s+encontros?",
            blob,
        )
    )
    campo_comunidade = bool(
        re.search(
            r"bairro|comunidade|associa[cç][aã]o|moradores|poder\s+p[uú]blico|"
            r"of[ií]cio|campo|coleta\s+de\s+dados|pesquisa\s+de\s+campo|"
            r"sa[ií]da|territ[oó]rio",
            blob,
        )
    )
    etico_sensivel = bool(
        re.search(
            r"viol[eê]ncia|inseguran[cç]a|criminalidade|abuso|trauma|"
            r"[eé]tico|sens[ií]vel|privacidade|exposição",
            blob,
        )
    )
    comunicacao_publica = bool(
        re.search(
            r"apresenta[cç][aã]o|audi[eê]ncia|pitch|of[ií]cio|redação|"
            r"argumenta[cç][aã]o|p[uú]blico|feira|mostra",
            blob,
        )
    )
    score = sum(
        [
            2 if interdisciplinar else 0,
            2 if multi_aula else 0,
            2 if campo_comunidade else 0,
            1 if etico_sensivel else 0,
            1 if comunicacao_publica else 0,
        ]
    )
    return {
        "interdisciplinar": interdisciplinar,
        "multi_aula": multi_aula,
        "campo_comunidade": campo_comunidade,
        "etico_sensivel": etico_sensivel,
        "comunicacao_publica": comunicacao_publica,
        "score": score,
        "complexo": score >= 3,
    }


def _cards_plano_pedagogico(
    *,
    nome: str,
    etiqueta: str,
    desc_curta: str,
    problema: str,
    contexto: str,
    trecho: str,
    gancho: str,
) -> tuple[list[dict], str, int]:
    """
    Plano de 5–7 cards para metodologias sem mecânica em METODOLOGIAS_DB.
    Mantém o nome do catálogo; densifica conforme a complexidade do relato.
    """
    sinais = _sinais_complexidade_projeto(problema, contexto)
    tema = trecho or frase_tema_do_relato(problema)
    ctx = contexto_seguro_para_ui(contexto, problema)
    mec_base = desc_curta or (
        f"prática ativa com «{nome}» (grupo {etiqueta}), "
        f"com mediação do professor e evidência de aprendizagem"
    )
    adapt = gancho or (
        f"Conecte a dinâmica ao que a turma enfrenta em torno de «{tema}»."
    )

    cards: list[dict] = [
        {
            "titulo_do_card": "Abrir a missão com a turma",
            "objetivo": (
                f"Deixar claro o objetivo de aprendizagem e o papel de «{nome}» "
                f"no desafio «{tema}»."
            ),
            "mecanica_passo_a_passo": (
                f"Apresente a missão em 5–8 minutos, cite o trecho do desafio "
                f"(«{tema}») e explique por que «{nome}» (grupo {etiqueta}) "
                f"ajuda a turma neste ponto. Combine critérios de sucesso da aula "
                f"e combine o tempo. Adaptação: {adapt}"
            ),
            "dica_de_facilitacao": (
                "Escreva a missão no quadro e peça a um estudante para reformular "
                "com as próprias palavras."
            ),
            "foco_da_metodologia_escolhida": f"abertura e contrato didático com {nome}",
            "duracao_minutos": 10,
        },
        {
            "titulo_do_card": "Organizar times e papéis",
            "objetivo": (
                "Formar equipes com papéis claros (líder, guardião do tempo, "
                "relator) para sustentar a prática."
            ),
            "mecanica_passo_a_passo": (
                f"Divida a turma em times de 3–5. Cada time define papéis e "
                f"registra o que já sabe sobre «{tema}» em 1 cartão coletivo. "
                f"No cenário de {ctx}, alinhe quem fala, quem anota e quem "
                f"apresenta. Use a lógica de «{nome}»: {mec_base}."
            ),
            "dica_de_facilitacao": (
                "Se houver turmas ou disciplinas diferentes, misture perfis "
                "para forçar articulação."
            ),
            "foco_da_metodologia_escolhida": f"organização colaborativa em {nome}",
            "duracao_minutos": 10,
        },
        {
            "titulo_do_card": f"Praticar a mecânica de {nome}",
            "objetivo": (
                f"Colocar a turma em atividade com a mecânica própria de «{nome}», "
                f"amarrada ao desafio real."
            ),
            "mecanica_passo_a_passo": (
                f"Conduza o núcleo de «{nome}». Peça que cada time produza uma "
                f"evidência parcial ligada a «{tema}» (mapa, lista, protótipo, "
                f"hipótese ou texto curto). Você circula, faz perguntas e "
                f"redireciona quando o grupo sair do foco. {adapt}"
            ),
            "dica_de_facilitacao": (
                "Intervenha com perguntas de mediação, não com respostas prontas."
            ),
            "foco_da_metodologia_escolhida": mec_base,
            "duracao_minutos": 20 if not sinais["complexo"] else 25,
        },
    ]

    if sinais["interdisciplinar"]:
        cards.append(
            {
                "titulo_do_card": "Articular saberes das áreas",
                "objetivo": (
                    "Fazer a turma conectar contribuições de diferentes áreas "
                    "em uma produção coerente."
                ),
                "mecanica_passo_a_passo": (
                    f"Peça que cada time nomeie o que vem de cada disciplina "
                    f"envolvida no desafio «{tema}» e onde essas peças se encontram. "
                    f"Monte um mural De/Para (área → contribuição → entrega comum). "
                    f"Com «{nome}», a articulação precisa aparecer na evidência "
                    f"parcial, não só na fala."
                ),
                "dica_de_facilitacao": (
                    "Exija pelo menos uma ponte explícita entre duas áreas "
                    "antes de avançar."
                ),
                "foco_da_metodologia_escolhida": "integração interdisciplinar",
                "duracao_minutos": 15,
            }
        )

    if sinais["etico_sensivel"] or sinais["campo_comunidade"]:
        cards.append(
            {
                "titulo_do_card": "Cuidar da ética e do contexto real",
                "objetivo": (
                    "Preparar coleta, linguagem e exposição de dados com "
                    "cuidado ético e respeito à comunidade."
                ),
                "mecanica_passo_a_passo": (
                    f"Antes de qualquer coleta ou publicação ligada a «{tema}», "
                    f"combine com a turma: o que pode ser compartilhado, o que "
                    f"fica anônimo, como falar com moradores/instituições e "
                    f"como registrar evidências sem expor pessoas. Registre "
                    f"um mini-protocolo ético do time."
                ),
                "dica_de_facilitacao": (
                    "Use casos hipotéticos se o tema for sensível demais "
                    "para relatos pessoais."
                ),
                "foco_da_metodologia_escolhida": "ética e responsabilidade social",
                "duracao_minutos": 12,
            }
        )

    cards.append(
        {
            "titulo_do_card": "Consolidar evidência e feedback",
            "objetivo": (
                "Tornar visível o que a turma aprendeu e o que ainda precisa "
                "avançar no projeto."
            ),
            "mecanica_passo_a_passo": (
                f"Cada time apresenta em 60–90s a evidência parcial de «{tema}». "
                f"Os pares dão feedback com rubrica curta (clareza, vínculo com "
                f"o desafio, próximo passo). Você registra 1 avanço e 1 lacuna "
                f"por time — isso alimenta a próxima aula."
            ),
            "dica_de_facilitacao": (
                "Peça evidência observável (foto, trecho, dado, rascunho), "
                "não só opinião."
            ),
            "foco_da_metodologia_escolhida": "avaliação formativa",
            "duracao_minutos": 12,
        }
    )

    if sinais["comunicacao_publica"] or sinais["campo_comunidade"]:
        cards.append(
            {
                "titulo_do_card": "Preparar entrega para o mundo real",
                "objetivo": (
                    "Ensaiar a comunicação formal da entrega (ofício, pitch, "
                    "apresentação à comunidade)."
                ),
                "mecanica_passo_a_passo": (
                    f"Com base em «{nome}», cada time estrutura a fala/texto "
                    f"para o público externo ligado a «{tema}»: problema, "
                    f"evidência, proposta e pedido. Ensaie 1 minuto e ajuste "
                    f"vocabulário para clareza cívica."
                ),
                "dica_de_facilitacao": (
                    "Separe linguagem escolar de linguagem pública; cobrem "
                    "precisão sem perder respeito."
                ),
                "foco_da_metodologia_escolhida": "comunicação e engajamento cívico",
                "duracao_minutos": 15,
            }
        )

    fechamento = {
        "titulo_do_card": "Fechar e planejar o próximo passo",
        "objetivo": (
            "Fechar a aula com checkout e um compromisso concreto "
            "para a continuidade do projeto."
        ),
        "mecanica_passo_a_passo": (
            f"Checkout rápido: cada estudante completa «Hoje aprendi… / "
            f"Ainda preciso… / Próximo passo…» ligado a «{tema}». "
            f"O líder de cada time anuncia a tarefa até o próximo encontro. "
            f"Você confirma o que entra no Kanban do desafio."
        ),
        "dica_de_facilitacao": (
            "Deixe o próximo passo escrito e visível antes de liberar a turma."
        ),
        "foco_da_metodologia_escolhida": "metacognição e continuidade",
        "duracao_minutos": 8,
    }

    # Limite EduScrum: até 7 cards — fechamento sempre por último
    if len(cards) >= 7:
        cards = cards[:6]
    cards.append(fechamento)
    total = sum(int(c.get("duracao_minutos") or 0) for c in cards)
    if sinais["complexo"] and total < 90:
        # Projetos densos pedem mais tempo (multi-aula / campo)
        extra = 90 - total
        cards[2]["duracao_minutos"] = int(cards[2].get("duracao_minutos") or 20) + extra
        total = sum(int(c.get("duracao_minutos") or 0) for c in cards)
    ctx_exec = "misto" if sinais["campo_comunidade"] else ("sala" if total <= 70 else "misto")
    return cards, ctx_exec, total


def _enriquecer_cards_com_complexidade(
    cards: list,
    *,
    problema: str,
    contexto: str,
    trecho: str,
    nome: str,
) -> list:
    """Se o DB trouxe poucos cards num projeto complexo, completa com fases pedagógicas."""
    sinais = _sinais_complexidade_projeto(problema, contexto)
    if not sinais["complexo"] or len(cards) >= 5:
        return cards
    tema = trecho or frase_tema_do_relato(problema)
    extras: list[dict] = []
    if sinais["interdisciplinar"] and len(cards) < 6:
        extras.append(
            {
                "titulo_do_card": "Articular saberes das áreas",
                "objetivo": (
                    "Conectar contribuições das disciplinas em uma produção coerente."
                ),
                "mecanica_passo_a_passo": (
                    f"Com «{nome}», peça que o time explicite o que cada área "
                    f"aporta a «{tema}» e onde essas peças se encontram na entrega."
                ),
                "dica_de_facilitacao": "Exija pelo menos uma ponte entre duas áreas.",
                "foco_da_metodologia_escolhida": "integração interdisciplinar",
                "duracao_minutos": 12,
            }
        )
    if (sinais["etico_sensivel"] or sinais["campo_comunidade"]) and len(cards) + len(extras) < 7:
        extras.append(
            {
                "titulo_do_card": "Protocolo ético e de campo",
                "objetivo": "Definir o que pode ser coletado, dito e publicado.",
                "mecanica_passo_a_passo": (
                    f"Antes de avançar em «{tema}», combine anonimato, consentimento "
                    f"e linguagem respeitosa com a comunidade."
                ),
                "dica_de_facilitacao": "Prefira casos hipotéticos se o tema for sensível.",
                "foco_da_metodologia_escolhida": "ética e responsabilidade social",
                "duracao_minutos": 10,
            }
        )
    out = list(cards) + extras
    return out[:7]


def _montar_caminho_hibrido(
    letra: str,
    tipo_ranking: str,
    opt: dict,
    *,
    problema: str,
    contexto: str,
    trecho_relato: str,
    refs_no_prompt: list[dict] | None = None,
    forced_mid: str | None = None,
    override_by_key: dict | None = None,
) -> dict:
    """Costura: id do catálogo 39 + gancho/hipótese LLM → cards do id_db (se houver)."""
    mid = forced_mid or _resolve_catalog_id(opt.get("id_metodologia"))
    entrada = resolver_entrada_catalogo(mid)
    if not entrada:
        print(
            f"[wizard] id fora do catálogo 39 ({opt.get('id_metodologia')!r}) "
            f"— fallback {_DEFAULT_METODOLOGIA_ID}",
            file=sys.stderr,
        )
        mid = _DEFAULT_METODOLOGIA_ID
        entrada = resolver_entrada_catalogo(mid) or {
            "id": mid,
            "nome": "Narrativas Transmídia em Rotação por Estações",
            "etiqueta": ETIQUETA_INDUTIVAS,
            "id_db": "criativa_narrativas_transmidia",
        }

    nome = str(entrada.get("nome") or "Metodologia Inov-Ativa").strip()
    etiqueta = etiqueta_publica(entrada.get("etiqueta"))
    id_db = entrada.get("id_db")
    pub = get_dinamica_by_id(entrada["id"]) or {}
    desc_curta = str(pub.get("descricao_curta") or "").strip()

    gancho = str(opt.get("gancho_adaptacao") or "").strip()
    trecho = trecho_relato or extrair_trecho_relato(problema)

    # Cards densos: preferir METODOLOGIAS_DB; senão plano pedagógico 5–7 etapas
    # amarrado ao relato (nunca 1 card genérico).
    db_data = get_metodologia(id_db) if id_db else None
    duracao_forcada: int | None = None
    if db_data and db_data.get("cards"):
        fonte = "metodologias_db"
        cards_src = db_data
        cards = copy.deepcopy(cards_src.get("cards") or [])
        cards = _enriquecer_cards_com_complexidade(
            cards,
            problema=problema,
            contexto=contexto,
            trecho=trecho,
            nome=nome,
        )
        ctx_exec = str(cards_src.get("contexto_execucao") or "sala")
    else:
        fonte = "catalogo_39_plano_pedagogico"
        cards, ctx_exec, duracao_forcada = _cards_plano_pedagogico(
            nome=nome,
            etiqueta=etiqueta,
            desc_curta=desc_curta,
            problema=problema,
            contexto=contexto,
            trecho=trecho,
            gancho=gancho,
        )
        cards_src = {
            "nome": nome,
            "categoria": etiqueta,
            "etiqueta": etiqueta,
            "descricao_curta": desc_curta,
            "cards": cards,
            "contexto_execucao": ctx_exec,
        }

    cards = _injetar_gancho_primeiro_card(cards, gancho)

    # Justificativa = mecânica do catálogo + encaixe no relato (gancho da IA)
    por_que = _por_que_usar_do_catalogo(
        cards_src,
        etiqueta=etiqueta,
        gancho=gancho,
        trecho=trecho,
    )
    dinamica = _dinamica_sala_do_catalogo(cards_src)

    hip_ia = str(opt.get("hipotese_teste") or "").strip()
    refs = refs_no_prompt or []
    hip_ok = False
    if hip_ia:
        corpus_local = corpus_textos_de_refs(refs)
        vaza = vaza_contra_corpus(hip_ia, corpus_local, problema)[0]
        ligada = vinculo_minimo_com_relato(hip_ia, problema)
        hip_ok = (not vaza) and ligada
    if hip_ok:
        hipotese = completar_frase(hip_ia, LIMITE_HIPOTESE)
    else:
        tema = frase_tema_do_relato(problema)
        ctx_safe = contexto_seguro_para_ui(contexto, problema)
        hipotese = (
            f"Se você conduzir {nome} com a turma em torno de {tema}, "
            f"os estudantes praticam a aprendizagem de forma ativa "
            f"e você observa evidência do progresso em {ctx_safe}."
        )

    gancho_resumo = (
        completar_frase(gancho, LIMITE_GANCHO)
        if gancho
        else f"Adapte {nome} ao que a sua turma precisa praticar nesta aula."
    )

    sinais = _sinais_complexidade_projeto(problema, contexto)
    # Missão completa — nunca cortar o relato no meio da palavra/ideia.
    enfrentamento = completar_frase(
        (problema or trecho or "").strip() or "o desafio da turma",
        LIMITE_HIPOTESE,
    )
    missao = (
        f"Missão: conduzir «{nome}» para enfrentar «{enfrentamento}»"
        f"{' em um projeto interdisciplinar e com entrega no mundo real' if sinais['complexo'] else ''}."
    )
    total_cards = duracao_forcada or (
        duracao_total_cards(cards) if cards else 50
    )
    plano = _plano_padrao(
        missao,
        cards,
        contexto_execucao=ctx_exec or cards_src.get("contexto_execucao") or "sala",
        duracao_total_estimada_min=total_cards,
    )
    plano["fonte_cards"] = fonte
    plano["id_metodologia"] = entrada["id"]
    plano["complexidade_projeto"] = {
        k: sinais[k]
        for k in (
            "interdisciplinar",
            "multi_aula",
            "campo_comunidade",
            "etico_sensivel",
            "comunicacao_publica",
            "complexo",
            "score",
        )
    }

    caminho: dict = {
        "id": letra,
        "tipo_ranking": tipo_ranking,
        "titulo": f"{nome} no desafio da turma",
        "metodologia": nome,
        "quadrante": etiqueta,
        "etiqueta": etiqueta,
        "id_metodologia": entrada["id"],
        "resumo": gancho_resumo,
        "por_que_usar": por_que,
        "dinamica_sala": dinamica,
        "gancho_adaptacao": gancho_resumo,
        "hipotese_teste": hipotese,
        "trecho_relato_usado": trecho,
        "inspiracao_caso": None,
        "ancoragem_de_para": None,
        "plano_eduscrum": plano,
        "nome": nome,
        "categoria": etiqueta,
        "cards": cards,
    }
    if tipo_ranking == "adaptacao_hibrida":
        caminho["inspiracao_caso"] = gancho_resumo[:220]
        caminho["ancoragem_de_para"] = (
            f"[De: desafio do professor] -> [Para: {nome} ({entrada['id']})]"
        )
    # Governança escolar (fail-soft): injeta diretriz se houver override ativo
    try:
        from services.methodology_override_service import apply_override_to_caminho

        ov = (override_by_key or {}).get(entrada["id"])
        if ov:
            caminho = apply_override_to_caminho(caminho, ov)
    except Exception as exc:
        print(f"[wizard] override inject: {exc}", file=sys.stderr)
    return caminho


def _stitch_ranking_hibrido(
    raw: dict,
    problema: str,
    contexto: str,
    refs: list[dict],
    corpus_refs: list[str] | None = None,
    *,
    exclude_ids: set[str] | None = None,
    override_by_key: dict | None = None,
) -> dict:
    """
    Costura o JSON curto do LLM (A/B/C) com o catálogo canônico de 39.
    Sempre devolve plano com vários cards (DB ou plano pedagógico denso).
    """
    corpus = corpus_refs if corpus_refs is not None else _carregar_corpus_referencia_completo()
    base = _fallback_payload(problema, contexto, refs, corpus)
    if not isinstance(raw, dict):
        return base

    if isinstance(raw.get("caminhos"), list) and raw["caminhos"]:
        return _normalizar_payload(raw, problema, contexto, refs, corpus)

    trecho_ia = str(raw.get("trecho_relato_usado") or "").strip()
    if trecho_ia and jaccard_words(trecho_ia, problema) >= 0.12:
        trecho = trecho_ia[:220]
    else:
        trecho = extrair_trecho_relato(problema)

    caminhos_out = []
    used_mids: set[str] = set()
    for i, letra in enumerate(_IDS_RANKING):
        opt = raw.get(letra)
        if not isinstance(opt, dict):
            continue
        trecho_opt = str(opt.get("trecho_relato_usado") or "").strip()
        trecho_uso = (
            trecho_opt[:220]
            if trecho_opt and jaccard_words(trecho_opt, problema) >= 0.12
            else trecho
        )
        preferred = _resolve_catalog_id(opt.get("id_metodologia"))
        mid = _pick_metodologia_diversa(
            used_mids,
            preferred_id=preferred,
            slot=i,
            seed=problema or contexto or "",
            exclude_ids=exclude_ids,
        )
        used_mids.add(mid)
        caminhos_out.append(
            _montar_caminho_hibrido(
                letra,
                _TIPOS_RANKING[i],
                opt,
                problema=problema,
                contexto=contexto,
                trecho_relato=trecho_uso,
                refs_no_prompt=refs,
                forced_mid=mid,
                override_by_key=override_by_key,
            )
        )

    if len(caminhos_out) < 3:
        raise ValueError(
            f"Ranking híbrido incompleto: esperava A/B/C, veio {list(raw.keys())}"
        )

    causas = sanitizar_causas_ia(
        raw.get("causas") or raw.get("causas_raiz"),
        problema=problema,
        contexto=contexto,
        refs_no_prompt=refs,
        corpus_refs=corpus,
    )

    hipoteses = [c.get("hipotese_teste") or "" for c in caminhos_out]
    textos_causas = [
        f"{c.get('titulo', '')} {c.get('descricao', '')}" for c in causas
    ]
    qualidade = avaliar_qualidade(
        problema=problema,
        trecho_relato_usado=trecho,
        textos_hipoteses=hipoteses + [c.get("resumo") or "" for c in caminhos_out],
        textos_causas=textos_causas,
        refs_no_prompt=refs,
        n_causas_ia=contar_causas_ia(causas),
        corpus_refs=corpus,
    )
    if (
        qualidade.get("possivel_vazamento")
        or qualidade.get("causas_enlatadas")
        or qualidade.get("debug_ui")
        or qualidade.get("causas_ia_insuficientes")
        or qualidade.get("tokens_soltos")
    ):
        print(
            f"[wizard] ALERTA qualidade vazamento={qualidade.get('vazamento_score')} "
            f"enlatadas={qualidade.get('causas_enlatadas')} "
            f"debug_ui={qualidade.get('debug_ui')} "
            f"tokens_soltos={qualidade.get('tokens_soltos')} "
            f"causas_ia={contar_causas_ia(causas)} "
            f"ancoragem={qualidade.get('ancoragem_termos_ok')}",
            file=sys.stderr,
        )

    base["resumo_analise"] = (
        "Analisamos o seu relato e sugerimos três caminhos metodológicos "
        "para a turma. Cada opção parte do que você descreveu — "
        "escolha a que melhor se encaixa no seu contexto."
    )
    base["causas_raiz"] = causas
    base["caminhos"] = caminhos_out
    base["trecho_relato_usado"] = qualidade.get("trecho_relato_usado") or trecho
    base["qualidade"] = {
        "vinculo_relato_ok": qualidade.get("vinculo_relato_ok"),
        "vinculo_relato_score": qualidade.get("vinculo_relato_score"),
        "possivel_vazamento": qualidade.get("possivel_vazamento"),
        "vazamento_score": qualidade.get("vazamento_score"),
        "ancoragem_termos_ok": qualidade.get("ancoragem_termos_ok"),
        "causas_enlatadas": qualidade.get("causas_enlatadas"),
        "debug_ui": qualidade.get("debug_ui"),
        "tokens_soltos": qualidade.get("tokens_soltos"),
        "causas_ia_insuficientes": qualidade.get("causas_ia_insuficientes"),
        "precisa_retry": qualidade.get("precisa_retry"),
        "fonte": "hibrido_ia",
    }
    return forcar_ancoragem_payload(
        base, problema=problema, contexto=contexto, corpus_refs=corpus
    )


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
    complementacao = str(data.get("complementacao") or "").strip()
    # Complementação soma ao relato (não substitui) e força reprocessamento completo.
    if complementacao:
        marcador = "Complemento do professor:"
        if marcador.lower() not in problema.lower() or complementacao.lower() not in problema.lower():
            problema = f"{problema.rstrip()}\n\n{marcador} {complementacao}"
        print(
            f"[wizard] complementacao_aplicada chars={len(complementacao)}",
            file=sys.stderr,
        )

    # Checagem determinística ANTES de qualquer chamada de IA
    motivo_curto = relato_insufficiente(problema)
    if motivo_curto:
        return jsonify({"error": motivo_curto, "code": "RELATO_CURTO"}), 400

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

    t0 = time.monotonic()
    corpus_refs = _carregar_corpus_referencia_completo()

    try:
        refs = _buscar_problemas_referencia(problema, contexto)
    except Exception as exc:
        print(f"[wizard] DB error: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao consultar a base de problemas."}), 500

    # Âncoras de estilo: no máx. 2, texto curto — nunca empilhar a base
    refs_prompt = refs[:WIZARD_REF_LIMIT]

    def _clip(val: object, n: int = 70) -> str:
        s = " ".join(str(val or "").split())
        return s if len(s) <= n else s[: n - 1] + "…"

    if refs_prompt:
        bloco_ref = "\n".join(
            [
                f"- (estilo) {_clip(r.get('categoria_prob'), 36)}: {_clip(r.get('desc_prob'), 70)}"
                for r in refs_prompt
            ]
        )
    else:
        bloco_ref = (
            "- (estilo) Engajamento: turma dispersa precisa de papéis claros e entrega curta."
        )

    # Overrides da escola (fail-soft): nunca bloqueia freemium / criação de aula
    override_by_key: dict = {}
    exclude_ids: set[str] = set()
    try:
        from services.methodology_override_service import (
            blocked_ids_for_vector,
            overrides_map_for_professor,
        )

        override_by_key = overrides_map_for_professor(int(id_clie))
        exclude_ids = blocked_ids_for_vector(int(id_clie), "desafio")
    except Exception as exc:
        print(f"[wizard] overrides load: {exc}", file=sys.stderr)
        override_by_key = {}
        exclude_ids = set()

    diretrizes_escola = [
        ov
        for ov in override_by_key.values()
        if ov.get("diretriz_customizada") and ov.get("disponivel_desafio", True)
    ]
    system_prompt = build_estruturar_system_prompt(
        bloco_ref,
        exclude_ids=exclude_ids,
        diretrizes_escola=diretrizes_escola,
    )

    problema_limpo = texto_professor_limpo(problema) or problema
    ctx_prompt = contexto_seguro_para_ui(contexto, problema, corpus_refs)
    user_content = (
        f"PROBLEMA DO PROFESSOR:\n{problema_limpo}\n\n"
        f"LOCALIZAÇÃO / CONTEXTO:\n{ctx_prompt}\n"
    )
    if complementacao:
        user_content += (
            "\nINSTRUÇÃO: o professor acabou de complementar o relato. "
            "Reescreva as 3 causas do zero com esse detalhe novo — "
            "não concatene o texto antigo de 'hipótese a aprofundar'.\n"
        )

    tokens_system = estimate_tokens(system_prompt)
    tokens_user = estimate_tokens(user_content)
    print(
        f"[wizard] prompt_tokens_est system={tokens_system} user={tokens_user} "
        f"total={tokens_system + tokens_user} refs={len(refs_prompt)} "
        f"overrides={len(override_by_key)} blocked_desafio={len(exclude_ids)}",
        file=sys.stderr,
    )

    usou_fallback = False
    usou_retry = False
    json_prefill = "{"
    model_id = WIZARD_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    print(
        f"[wizard] model_escolhido={model_id} budget_s={WIZARD_TOTAL_BUDGET_SEC} "
        f"read_timeout_s={WIZARD_BEDROCK_READ_TIMEOUT} max_tokens={BEDROCK_MAX_TOKENS} "
        f"retry_enabled={WIZARD_RETRY_ENABLED}",
        file=sys.stderr,
    )
    raw = None
    try:
        bedrock = _get_bedrock_runtime_client()
        remaining = WIZARD_TOTAL_BUDGET_SEC - (time.monotonic() - t0)
        if remaining < 5:
            raise TimeoutError("Orçamento de 30s esgotado antes da IA")
        # Chamada única sob SLA (sem 2ª rodada por padrão)
        raw = _invoke_estruturar_bedrock_deadline(
            bedrock=bedrock,
            model_id=model_id,
            system_prompt=system_prompt,
            user_content=user_content,
            max_tokens=BEDROCK_MAX_TOKENS,
            json_prefill=json_prefill,
            deadline_sec=remaining,
        )
        elapsed = time.monotonic() - t0
        print(
            f"[wizard] bedrock_ok keys={list(raw.keys()) if isinstance(raw, dict) else type(raw)} "
            f"elapsed_s={elapsed:.1f}",
            file=sys.stderr,
        )
        payload = _stitch_ranking_hibrido(
            raw,
            problema,
            contexto,
            refs_prompt,
            corpus_refs,
            exclude_ids=exclude_ids,
            override_by_key=override_by_key,
        )

        # Retry opcional (off por padrão no SLA 30s)
        q0 = payload.get("qualidade") or {}
        remaining = WIZARD_TOTAL_BUDGET_SEC - (time.monotonic() - t0)
        if (
            WIZARD_RETRY_ENABLED
            and q0.get("precisa_retry")
            and remaining >= WIZARD_RETRY_MIN_REMAINING_SEC
        ):
            print(
                f"[wizard] retry_unico motivo vinculo={q0.get('vinculo_relato_ok')} "
                f"vazamento={q0.get('possivel_vazamento')} "
                f"ancoragem={q0.get('ancoragem_termos_ok')} "
                f"enlatadas={q0.get('causas_enlatadas')} "
                f"remaining_s={remaining:.1f}",
                file=sys.stderr,
            )
            user_retry = (
                user_content
                + "\n\nATENÇÃO: a resposta anterior ficou genérica ou desconectada. "
                "Reescreva causas e hipotese_teste citando termos CONCRETOS do "
                "PROBLEMA DO PROFESSOR (nomes próprios, lugares, turmas, prazos). "
                "PROIBIDO usar faltas, leituras obrigatórias ou absenteísmo se isso "
                "não estiver no relato."
            )
            raw2 = _invoke_estruturar_bedrock_deadline(
                bedrock=bedrock,
                model_id=model_id,
                system_prompt=system_prompt,
                user_content=user_retry,
                max_tokens=BEDROCK_MAX_TOKENS,
                json_prefill=json_prefill,
                deadline_sec=remaining,
            )
            payload = _stitch_ranking_hibrido(
                raw2,
                problema,
                contexto,
                refs_prompt,
                corpus_refs,
                exclude_ids=exclude_ids,
                override_by_key=override_by_key,
            )
            usou_retry = True
            q1 = dict(payload.get("qualidade") or {})
            q1["retry_aplicado"] = True
            payload["qualidade"] = q1
        elif q0.get("precisa_retry"):
            print(
                f"[wizard] retry_pulado enabled={WIZARD_RETRY_ENABLED} "
                f"remaining_s={remaining:.1f}",
                file=sys.stderr,
            )
    except Exception as exc:
        print(
            f"[wizard] Bedrock/fallback: {exc} elapsed_s={time.monotonic() - t0:.1f}",
            file=sys.stderr,
        )
        payload = _fallback_payload(problema, contexto, refs_prompt, corpus_refs)
        usou_fallback = True
        # Fallback também respeita vetores/diretrizes quando possível
        try:
            if isinstance(payload, dict) and payload.get("caminhos"):
                from services.methodology_override_service import apply_override_to_caminho

                novos = []
                for c in payload["caminhos"]:
                    mid = _resolve_catalog_id(
                        (c or {}).get("id_metodologia") or (c or {}).get("metodologia")
                    )
                    if mid and mid in exclude_ids:
                        continue
                    ov = override_by_key.get(mid) if mid else None
                    novos.append(apply_override_to_caminho(c, ov) if ov else c)
                if len(novos) >= 1:
                    payload["caminhos"] = novos
        except Exception as exc2:
            print(f"[wizard] fallback override: {exc2}", file=sys.stderr)

    # Defesa determinística + barreira final (tabela inteira de refs)
    payload = forcar_ancoragem_payload(
        payload, problema=problema, contexto=contexto, corpus_refs=corpus_refs
    )
    payload = aplicar_barreira_final_payload(
        payload, problema=problema, contexto=contexto, corpus_refs=corpus_refs
    )
    # Após complementação, nenhuma causa deve continuar pedindo complemento
    if complementacao:
        for c in payload.get("causas_raiz") or []:
            if isinstance(c, dict):
                c["precisa_complemento"] = False
                c.pop("pergunta_complemento", None)

    qualidade = dict(payload.get("qualidade") or {})
    textos_c = [
        f"{c.get('titulo', '')} {c.get('descricao', '')}"
        for c in (payload.get("causas_raiz") or [])
        if isinstance(c, dict)
    ]
    textos_h = [
        c.get("hipotese_teste") or ""
        for c in (payload.get("caminhos") or [])
        if isinstance(c, dict)
    ]
    qualidade.update(
        avaliar_qualidade(
            problema=problema,
            trecho_relato_usado=payload.get("trecho_relato_usado"),
            textos_hipoteses=textos_h,
            textos_causas=textos_c,
            refs_no_prompt=refs_prompt,
            n_causas_ia=contar_causas_ia(payload.get("causas_raiz")),
            corpus_refs=corpus_refs,
        )
    )
    qualidade["retry_aplicado"] = usou_retry
    qualidade["complementacao"] = bool(complementacao)
    qualidade["fonte"] = "fallback_local" if usou_fallback else qualidade.get("fonte") or "hibrido_ia"
    payload["qualidade"] = qualidade

    creditos_restantes = saldo
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

    print(
        f"[wizard] qualidade vinculo_ok={qualidade.get('vinculo_relato_ok')} "
        f"vazamento={qualidade.get('possivel_vazamento')} "
        f"ancoragem={qualidade.get('ancoragem_termos_ok')} "
        f"debug_ui={qualidade.get('debug_ui')} "
        f"barreira={qualidade.get('barreira_final_bloqueios')} "
        f"causas_ia={contar_causas_ia(payload.get('causas_raiz'))} "
        f"retry={usou_retry} fallback={usou_fallback} "
        f"complementacao={bool(complementacao)}",
        file=sys.stderr,
    )

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
            "trecho_relato_usado": payload.get("trecho_relato_usado"),
            "referencial": payload.get("referencial"),
            "fallback": usou_fallback,
            "creditos_ia": creditos_restantes,
            "qualidade": qualidade,
            "prompt_tokens_est": {
                "system": tokens_system,
                "user": tokens_user,
                "total": tokens_system + tokens_user,
                "refs": len(refs_prompt),
                "retry": usou_retry,
                "complementacao": bool(complementacao),
            },
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

    # Garante auditoria da versão do override no plano persistido
    versao = (
        caminho.get("metodologia_override_versao_aplicada")
        or (caminho.get("escola_override") or {}).get("versao")
        or plano.get("metodologia_override_versao_aplicada")
    )
    if versao is not None:
        try:
            plano["metodologia_override_versao_aplicada"] = int(versao)
        except (TypeError, ValueError):
            pass
    if caminho.get("escola_override") and not plano.get("escola_override"):
        plano["escola_override"] = caminho.get("escola_override")

    return jsonify(
        {
            "status": "success",
            "hipotese_teste": caminho.get("hipotese_teste"),
            "plano_eduscrum": plano,
            "caminho_id": caminho.get("id"),
            "caminho_titulo": caminho.get("titulo"),
            "escola_override": caminho.get("escola_override"),
            "metodologia_override_versao_aplicada": plano.get(
                "metodologia_override_versao_aplicada"
            ),
        }
    )


@wizard_bp.get("/api/wizard/metodologia-overrides")
def list_metodologia_overrides_professor():
    """Consulta os overrides ativos da instituição do professor (transparência / debug)."""
    user = session.get("user") or {}
    id_clie = user.get("id_clie")
    if not id_clie:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        from services.methodology_override_service import overrides_map_for_professor

        m = overrides_map_for_professor(int(id_clie))
        return jsonify(
            {
                "success": True,
                "overrides": list(m.values()),
                "total": len(m),
            }
        )
    except Exception as exc:
        print(f"[wizard] list overrides: {exc}", file=sys.stderr)
        return jsonify({"success": True, "overrides": [], "total": 0})

