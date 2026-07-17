"""Wizard Mesa do Inovador — fluxo guiado (problema → EduScrum).

Usa o DB configurado em DB_NAME (local: inove4us) e a base
ctdi_problemas_referencia para ancorar a análise.
"""

from __future__ import annotations

import json
import os
import re
import sys

import boto3
from botocore.config import Config
from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from db import consumir_credito_ia, get_conn, get_creditos_ia

wizard_bp = Blueprint("wizard", __name__)

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")


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
        config=Config(connect_timeout=8, read_timeout=60, retries={"max_attempts": 1}),
    )


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


def _buscar_problemas_referencia(problema: str, contexto: str, limit: int = 5) -> list[dict]:
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


def _plano_padrao(missao: str, tarefas: list[str]) -> dict:
    cores = ["#FDE68A", "#FDBA74", "#FCA5A5", "#A7F3D0", "#BFDBFE"]
    kanban = []
    for i, t in enumerate(tarefas[:5]):
        kanban.append(
            {
                "id": f"t{i + 1}",
                "titulo": t,
                "coluna": "para_fazer",
                "cor": cores[i % len(cores)],
            }
        )
    return {
        "missao": missao,
        "papeis": {
            "lider": "Líder — organiza o time e garante o foco na missão",
            "guardiao": "Guardião do Tempo — controla o timebox e o ritmo",
            "apresentador": "Apresentador — sintetiza e compartilha a entrega",
        },
        "tarefas_kanban": kanban,
        "timebox": [
            {"fase": "Planejamento", "minutos": 5, "descricao": "Combinar missão e papéis"},
            {"fase": "Ação", "minutos": 35, "descricao": "Executar tarefas no Kanban"},
            {"fase": "Retrospectiva", "minutos": 10, "descricao": "Compartilhar aprendizados"},
        ],
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
        "titulo": "Times EduScrum com missão clara",
        "resumo": (
            f"Organizar a turma em times com papéis (Líder, Guardião, Apresentador) "
            f"para enfrentar «{categoria}» em um ciclo de aula."
        ),
        "hipotese_teste": (
            f"Se organizarmos times EduScrum para atacar «{problema[:120]}», "
            f"os alunos aprenderão a colaborar com responsabilidade e produzirão "
            f"uma entrega concreta em um timebox de 50 minutos."
        ),
        "plano_eduscrum": _plano_padrao(
            f"Missão: transformar o problema «{problema[:80]}» em aprendizagem ativa.",
            [
                "Mapear o problema em 3 frases com evidências da turma",
                "Escolher uma intervenção prática inspirada na referência CMU",
                "Prototipar a intervenção em um mini-roteiro de 10 minutos",
                "Testar o protótipo com o próprio time",
                "Preparar pitch de 60 segundos com o aprendizado",
            ],
        ),
    }

    caminho_b = {
        "id": "B",
        "titulo": "Laboratório de hipótese rápida",
        "resumo": (
            f"Tratar a aula como experimento: formular hipótese, testar micro-ação "
            f"e medir sinal de aprendizagem. Âncora: {str(solucao)[:120]}."
        ),
        "hipotese_teste": (
            f"Se aplicarmos um micro-experimento baseado em «{str(solucao)[:100]}», "
            f"os alunos aprenderão a validar ideias com evidência e ajustarão a prática "
            f"ainda dentro da mesma aula."
        ),
        "plano_eduscrum": _plano_padrao(
            f"Missão: validar em aula uma hipótese sobre «{problema[:80]}».",
            [
                "Escrever a hipótese no formato Se X, então Y",
                "Definir o sinal de sucesso observável em 35 minutos",
                "Rodar o micro-experimento no time",
                "Coletar 3 evidências (o que vimos / o que aprendemos)",
                "Decidir: manter, ajustar ou descartar a hipótese",
            ],
        ),
    }

    return {
        "causas_raiz": causas,
        "caminhos": [caminho_a, caminho_b],
        # Campos de topo exigidos pelo contrato — preenchidos quando o professor escolhe
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


def _normalizar_payload(raw: dict, problema: str, contexto: str, refs: list[dict]) -> dict:
    base = _fallback_payload(problema, contexto, refs)
    if not isinstance(raw, dict):
        return base

    causas = raw.get("causas_raiz") or base["causas_raiz"]
    if isinstance(causas, list) and causas:
        base["causas_raiz"] = causas[:5]

    caminhos_in = raw.get("caminhos") or []
    caminhos_out = []
    for i, c in enumerate(caminhos_in[:2]):
        if not isinstance(c, dict):
            continue
        fallback = base["caminhos"][i] if i < len(base["caminhos"]) else base["caminhos"][0]
        plano = c.get("plano_eduscrum") or fallback["plano_eduscrum"]
        if not isinstance(plano, dict):
            plano = fallback["plano_eduscrum"]
        tarefas = plano.get("tarefas_kanban") or fallback["plano_eduscrum"]["tarefas_kanban"]
        if isinstance(tarefas, list) and tarefas and isinstance(tarefas[0], str):
            plano = _plano_padrao(
                plano.get("missao") or fallback["plano_eduscrum"]["missao"],
                tarefas,
            )
        else:
            plano.setdefault("missao", fallback["plano_eduscrum"]["missao"])
            plano.setdefault("papeis", fallback["plano_eduscrum"]["papeis"])
            plano.setdefault("timebox", fallback["plano_eduscrum"]["timebox"])
            plano["tarefas_kanban"] = tarefas or fallback["plano_eduscrum"]["tarefas_kanban"]

        caminhos_out.append(
            {
                "id": str(c.get("id") or ("A" if i == 0 else "B")),
                "titulo": c.get("titulo") or fallback["titulo"],
                "resumo": c.get("resumo") or fallback["resumo"],
                "hipotese_teste": c.get("hipotese_teste") or fallback["hipotese_teste"],
                "plano_eduscrum": plano,
            }
        )

    if len(caminhos_out) < 2:
        caminhos_out = base["caminhos"]

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

    bloco_ref = "\n".join(
        [
            f"- [{r['id_prob']}] {r['grupo_prob']} › {r['categoria_prob']}: "
            f"{r['desc_prob']} | Causas: {r['razoes_prob']} | Soluções: {r['solucoes_prob']}"
            for r in refs
        ]
    ) or "Sem matches fortes — use heurística pedagógica sólida."

    system_prompt = f"""
Você é Designer Instrucional Sênior especialista em EduScrum e metodologias ativas (LeAction).
Transforme o problema do professor em um pacote estruturado para um fluxo guiado de inovação em sala.

REGRAS:
1. Escreva EXCLUSIVAMENTE em Português do Brasil.
2. Ancore causas e soluções na BASE DE PROBLEMAS abaixo (quando fizer sentido).
3. Proponha EXATAMENTE 2 caminhos de solução distintos e viáveis em uma aula.
4. Cada caminho deve trazer hipótese no formato: "Se fizermos X, os alunos aprenderão Y".
5. Cada plano EduScrum deve ter 3 a 5 tarefas práticas para o Kanban (coluna para_fazer).
6. Timebox padrão sugerido: 5 min Planejamento, 35 min Ação, 10 min Retrospectiva.
7. Retorne SOMENTE JSON limpo (sem markdown).

BASE DE PROBLEMAS (ctdi_problemas_referencia):
{bloco_ref}

Formato exato:
{{
  "causas_raiz": [
    {{"titulo": "...", "descricao": "...", "origem": "base_referencia|contexto_professor|heuristica"}}
  ],
  "caminhos": [
    {{
      "id": "A",
      "titulo": "...",
      "resumo": "...",
      "hipotese_teste": "Se fizermos X, os alunos aprenderão Y",
      "plano_eduscrum": {{
        "missao": "...",
        "papeis": {{
          "lider": "...",
          "guardiao": "...",
          "apresentador": "..."
        }},
        "tarefas_kanban": [
          {{"id": "t1", "titulo": "...", "coluna": "para_fazer", "cor": "#FDE68A"}}
        ],
        "timebox": [
          {{"fase": "Planejamento", "minutos": 5, "descricao": "..."}},
          {{"fase": "Ação", "minutos": 35, "descricao": "..."}},
          {{"fase": "Retrospectiva", "minutos": 10, "descricao": "..."}}
        ]
      }}
    }},
    {{ "id": "B", "...": "segundo caminho completo no mesmo formato" }}
  ]
}}
"""

    user_content = (
        f"PROBLEMA DO PROFESSOR:\n{problema}\n\n"
        f"LOCALIZAÇÃO / CONTEXTO:\n{contexto or 'Não informado'}\n\n"
        f"id_clie: {id_clie}"
    )

    usou_fallback = False
    try:
        bedrock = _get_bedrock_runtime_client()
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3200,
                "temperature": 0.55,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}],
            }
        )
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        texto = json.loads(response.get("body").read())["content"][0]["text"].strip()
        raw = _extrair_json(texto)
        payload = _normalizar_payload(raw, problema, contexto, refs)
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
