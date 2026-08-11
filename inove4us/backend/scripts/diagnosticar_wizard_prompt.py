"""Diagnóstico de tamanho do prompt do wizard (sem alterar produção).

Por padrão NÃO chama Bedrock. Use --invoke-bedrock apenas com credenciais
já configuradas no ambiente (não embute secrets).

Uso:
  python scripts/diagnosticar_wizard_prompt.py
  python scripts/diagnosticar_wizard_prompt.py --invoke-bedrock
  python scripts/diagnosticar_wizard_prompt.py --cenario curto
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Garante imports do backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.metodologia_keyword_matcher import (  # noqa: E402
    format_top_log,
    rankear_metodologias_por_keywords,
)
from prompts.inov_ativas import (  # noqa: E402
    build_estruturar_system_prompt,
    medir_componentes_entrada_prompt,
)
from wizard_qualidade import montar_user_content_estruturar  # noqa: E402

# Âncoras sintéticas de estilo (mesmo formato do wizard; sem conteúdo real de DB).
BLOCO_REF_DIAG = (
    "- (estilo) Engajamento: turma dispersa precisa de papéis claros e entrega curta.\n"
    "- (estilo) Investigação: problema local com coleta de evidências e síntese."
)


def _cenario_curto() -> dict:
    return {
        "nome": "curto",
        "problema": "Os alunos precisam investigar o desperdício de água na escola.",
        "objetivo": "Propor uma solução prática.",
        "turma_nivel": "8º ano",
        "duracao": "4 aulas",
        "contexto": "",
        "disciplina_area": "",
        "metodologia_id": "",
        "metodologia_nome": "",
    }


def _cenario_medio() -> dict:
    problema = (
        "Na escola municipal, a turma do 9º ano está com dificuldade para conectar "
        "conteúdo de ciências com o cotidiano. Quero que investiguem o descarte "
        "incorreto de lixo reciclável nos corredores e na cantina, mapeiem pontos "
        "críticos, conversem com a equipe de limpeza e proponham melhorias viáveis "
        "para a gestão escolar. O desafio é engajar alunos que costumam ficar "
        "passivos em atividades teóricas e transformar a observação em um plano "
        "concreto de ação, com papéis claros, coleta de dados simples e uma "
        "apresentação final para a coordenação. Há duas aulas por semana e pouco "
        "tempo de laboratório; precisamos de uma sequência que caiba em sala, "
        "com etapas curtas, evidências registradas e reflexão coletiva."
    )
    # Completa até ~800–1500 chars com contexto pedagógico genérico.
    contexto = (
        "Contexto adicional: a escola já tem coleta seletiva parcial, mas as "
        "lixeiras são pouco usadas. Alguns alunos participam do grêmio. A família "
        "pede projetos com impacto local. Materiais disponíveis: cartolina, "
        "celulares para fotos (com autorização) e uma sala de multimídia uma vez "
        "por semana. Avaliação deve valorizar colaboração e argumentação, não só "
        "o produto final. Evitar atividades que dependam de saída de campo longa."
    )
    return {
        "nome": "medio",
        "problema": problema,
        "objetivo": "Mapear o problema, propor melhorias e apresentar evidências à coordenação.",
        "turma_nivel": "9º ano",
        "duracao": "6 aulas",
        "contexto": contexto,
        "disciplina_area": "Ciências",
        "metodologia_id": "",
        "metodologia_nome": "",
    }


def _cenario_longo() -> dict:
    # Versão anonimizada/sintética (~3500–4500 chars) inspirada no cenário epidemiológico.
    problema = (
        "Projeto interdisciplinar de um semestre: a turma investigará a presença "
        "e o ciclo do Aedes aegypti no entorno da escola, com foco em prevenção "
        "da dengue. Etapa 1 — investigação: levantamento de conhecimento prévio, "
        "leitura de boletins epidemiológicos públicos (dados agregados, sem "
        "identificar pessoas) e definição de perguntas de pesquisa. Etapa 2 — "
        "mapeamento: observação segura de possíveis criadouros em áreas "
        "permitidas (pátio, jardins, calhas visíveis), registro fotográfico "
        "autorizado e preenchimento de fichas simples de risco. Etapa 3 — "
        "análise: organização dos achados em mapas mentais ou tabelas, "
        "comparação com indicadores regionais e discussão sobre fatores "
        "ambientais e comportamentais. Etapa 4 — prototipagem: criação de "
        "materiais educativos (cartazes, podcasts curtos ou maquetes) e de um "
        "roteiro de campanha de conscientização para a comunidade escolar. "
        "Etapa 5 — campanha: aplicação do plano em horários combinados com a "
        "coordenação, coleta de feedback de colegas e funcionários, ajustes "
        "rápidos. Etapa 6 — síntese semestral: relatório coletivo, exposição "
        "e autoavaliação dos papéis (investigador, comunicador, mediador). "
        "Restrições: sem manejo direto de criadouros com risco; sem dados "
        "pessoais sensíveis; atividades de campo apenas com autorização e "
        "supervisão. Objetivo pedagógico: articular biologia, geografia e "
        "língua portuguesa; praticar pensamento científico, colaboração e "
        "comunicação pública. Duração prevista: um semestre letivo, com "
        "encontros semanais de 50 minutos e dois blocos extras para "
        "prototipagem e campanha. A turma tem 32 alunos, níveis heterogêneos "
        "de leitura e alguns estudantes com dificuldade de participação oral. "
        "Precisamos de metodologias que sustentem investigação prolongada, "
        "entregas intermediárias e um produto final comunicável, sem virar "
        "apenas exposição teórica sobre dengue."
    )
    contexto = (
        "A escola fica em região com histórico sazonal de notificações de dengue "
        "(dados públicos). Há parceria informal com a unidade de saúde para "
        "palestras genéricas, sem acesso a prontuários. Biblioteca escolar "
        "oferece textos adaptados. O semestre inclui feira de ciências na "
        "semana 14. Famílias devem ser informadas do escopo do projeto. "
        "Avaliação formativa a cada etapa (rubrica de colaboração, qualidade "
        "das evidências e clareza da campanha). Se chover forte, o mapeamento "
        "externo é substituído por análise de fotos já existentes e "
        "simulação em sala. O professor de biologia coordena; português apoia "
        "os textos da campanha; geografia apoia o mapeamento. Queremos evitar "
        "atividades que gerem medo ou estigma; o tom é preventivo e científico. "
        "Materiais: fichas impressas, projetor, materiais de artesanato e "
        "acesso limitado à internet na sala de informática duas vezes ao mês. "
        "Cronograma indicativo: semanas 1–3 investigação documental; 4–6 "
        "mapeamento supervisionado; 7–9 análise e síntese; 10–12 prototipagem "
        "de materiais; 13–14 campanha e ajustes; 15–16 exposição e "
        "autoavaliação. Critérios de sucesso: participação de pelo menos 80% "
        "da turma nas entregas intermediárias, campanha compreensível para "
        "visitantes leigos e relatório final com evidências e limitações "
        "explícitas. Observação: este parágrafo é sintético/anonimizado para "
        "diagnóstico de tamanho de prompt — não contém dados reais de alunos."
        + (" Ampliação genérica de contexto para atingir faixa longa." * 8)
    )
    return {
        "nome": "longo",
        "problema": problema,
        "objetivo": (
            "Conduzir investigação, mapeamento, prototipagem e campanha preventiva "
            "ao longo do semestre, com entregas intermediárias avaliáveis."
        ),
        "turma_nivel": "1º ano EM",
        "duracao": "1 semestre",
        "contexto": contexto,
        "disciplina_area": "Biologia (interdisciplinar)",
        "metodologia_id": "",
        "metodologia_nome": "",
    }


CENARIOS = {
    "curto": _cenario_curto,
    "medio": _cenario_medio,
    "longo": _cenario_longo,
}


def _montar_cenario(dados: dict) -> dict:
    system_prompt = build_estruturar_system_prompt(
        BLOCO_REF_DIAG,
        exclude_ids=set(),
        diretrizes_escola=[],
        metodologia_obrigatoria_id=dados.get("metodologia_id") or None,
        metodologia_obrigatoria_nome=dados.get("metodologia_nome") or None,
    )
    user_content = montar_user_content_estruturar(
        problema_limpo=dados["problema"],
        objetivo=dados.get("objetivo") or "",
        turma_nivel=dados.get("turma_nivel") or "",
        disciplina_area=dados.get("disciplina_area") or "",
        duracao=dados.get("duracao") or "",
        contexto_seguro=dados.get("contexto") or "",
        metodologia_nome=dados.get("metodologia_nome") or "",
        metodologia_id=dados.get("metodologia_id") or "",
    )
    partes = medir_componentes_entrada_prompt(
        BLOCO_REF_DIAG,
        exclude_ids=set(),
        diretrizes_escola=[],
        metodologia_obrigatoria_id=dados.get("metodologia_id") or None,
        metodologia_obrigatoria_nome=dados.get("metodologia_nome") or None,
        system_prompt=system_prompt,
        user_content=user_content,
        ancoras_count=2,
    )
    ranking = rankear_metodologias_por_keywords(
        problema=dados["problema"],
        objetivo=dados.get("objetivo") or "",
        turma_nivel=dados.get("turma_nivel") or "",
        duracao=dados.get("duracao") or "",
        contexto=dados.get("contexto") or "",
        disciplina_nome=dados.get("disciplina_area") or "",
        top_n=5,
    )
    return {
        "dados": dados,
        "system_prompt": system_prompt,
        "user_content": user_content,
        "partes": partes,
        "ranking": ranking,
    }


def _imprimir_cenario(montado: dict, *, usage: dict | None = None) -> None:
    d = montado["dados"]
    p = montado["partes"]
    ranking = montado["ranking"]
    print(f"\n=== CENÁRIO: {d['nome']} ===")
    print(f"system_chars: {p['system_total_chars']}")
    print(f"catalogo_chars: {p['system_catalogo_chars']}")
    print(f"ancoras_chars: {p['system_ancoras_chars']} (count={p['ancoras_count']})")
    print(f"diretrizes_chars: {p['system_diretrizes_chars']}")
    print(f"obrigatoria_chars: {p['system_obrigatoria_chars']}")
    print(f"user_chars: {p['user_content_chars']}")
    print(f"problema_chars: {len(d['problema'])}")
    print(f"contexto_chars: {len(d.get('contexto') or '')}")
    print(f"matcher_top5: [{format_top_log(ranking, limite=5)}]")
    mid = d.get("metodologia_id") or ""
    print(f"metodologia_desejada_id: {mid or '(nenhuma)'}")
    if usage:
        for k in (
            "input_tokens",
            "output_tokens",
            "bedrock_latency_ms",
            "stop_reason",
        ):
            if usage.get(k) is not None:
                print(f"{k}: {usage[k]}")
        q = usage.get("qualidade") or {}
        if q:
            print(
                "qualidade: "
                f"json_ok={q.get('json_ok')} n_causas={q.get('n_causas')} "
                f"tem_abc={q.get('tem_abc')} ids_validos={q.get('ids_validos')} "
                f"ids_distintos={q.get('ids_distintos')} "
                f"familias_distintas={q.get('familias_distintas')} "
                f"ids={q.get('ids')} "
                f"causas_1frase={q.get('causas_uma_frase')} "
                f"ganchos_1frase={q.get('ganchos_uma_frase')} "
                f"hipoteses_1frase={q.get('hipoteses_uma_frase')}"
            )


def _info_max_tokens() -> None:
    # Importa constantes efetivas do wizard (sem alterar).
    from wizard_routes import (
        BEDROCK_MAX_TOKENS,
        BEDROCK_MODEL_ID,
        WIZARD_BEDROCK_MODEL_ID,
    )

    print("\n=== BEDROCK_MAX_TOKENS (somente leitura) ===")
    print(f"env BEDROCK_MAX_TOKENS: {os.environ.get('BEDROCK_MAX_TOKENS', '(unset → default 4096)')}")
    print(f"valor efetivo BEDROCK_MAX_TOKENS: {BEDROCK_MAX_TOKENS}")
    print("configurado em: wizard_routes.py (os.environ.get('BEDROCK_MAX_TOKENS', '4096'))")
    print("override específico do wizard para max_tokens: nenhum (usa BEDROCK_MAX_TOKENS)")
    print(f"modelo efetivo: {WIZARD_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID}")
    print("assistant prefill: \"{\"")
    print("nota: max_tokens é teto de saída, não tokens efetivamente consumidos.")


def _avaliar_qualidade_estrutural(parsed: dict) -> dict:
    """Flags estruturais sem logar texto do professor/modelo."""
    from prompts.inov_ativas import IDS_METODOLOGIA_CATALOGO
    from core.catalogo_metodologias_dia import entradas_catalogo_dia

    ids_ok = set(IDS_METODOLOGIA_CATALOGO)
    fam_por_id = {e["id"]: e["etiqueta"] for e in entradas_catalogo_dia()}
    causas = parsed.get("causas") if isinstance(parsed, dict) else None
    n_causas = len(causas) if isinstance(causas, list) else 0
    ids = []
    fams = []
    for chave in ("A", "B", "C"):
        bloco = (parsed or {}).get(chave) if isinstance(parsed, dict) else None
        mid = (bloco or {}).get("id_metodologia") if isinstance(bloco, dict) else None
        ids.append(mid)
        fams.append(fam_por_id.get(mid) if mid else None)

    def _uma_frase(txt: object) -> bool:
        s = " ".join(str(txt or "").split()).strip()
        if not s or s.endswith("…") or s.endswith("..."):
            return False
        # heurística: poucas sentenças
        return s.count(". ") + s.count("! ") + s.count("? ") <= 1

    ganchos_ok = all(
        _uma_frase(((parsed or {}).get(k) or {}).get("gancho_adaptacao"))
        for k in ("A", "B", "C")
        if isinstance((parsed or {}).get(k), dict)
    )
    hipoteses_ok = all(
        _uma_frase(((parsed or {}).get(k) or {}).get("hipotese_teste"))
        for k in ("A", "B", "C")
        if isinstance((parsed or {}).get(k), dict)
    )
    causas_ok = False
    if isinstance(causas, list) and n_causas == 3:
        causas_ok = all(
            isinstance(c, dict) and _uma_frase(c.get("descricao")) for c in causas
        )

    return {
        "json_ok": isinstance(parsed, dict),
        "n_causas": n_causas,
        "tem_abc": all(isinstance((parsed or {}).get(k), dict) for k in ("A", "B", "C")),
        "ids_validos": all(i in ids_ok for i in ids if i),
        "ids_distintos": len(set(ids)) == 3 and all(ids),
        "familias_distintas": len(set(fams)) == 3 and all(fams),
        "ids": ids,
        "causas_uma_frase": causas_ok,
        "ganchos_uma_frase": ganchos_ok,
        "hipoteses_uma_frase": hipoteses_ok,
    }


def _invoke_opcional(montado: dict) -> dict | None:
    from wizard_routes import (
        BEDROCK_MAX_TOKENS,
        BEDROCK_MODEL_ID,
        WIZARD_BEDROCK_MODEL_ID,
        _get_bedrock_runtime_client,
        _invoke_estruturar_bedrock,
    )

    model_id = WIZARD_BEDROCK_MODEL_ID or BEDROCK_MODEL_ID
    bedrock = _get_bedrock_runtime_client()
    t0 = time.perf_counter()
    parsed, meta = _invoke_estruturar_bedrock(
        bedrock=bedrock,
        model_id=model_id,
        system_prompt=montado["system_prompt"],
        user_content=montado["user_content"],
        max_tokens=BEDROCK_MAX_TOKENS,
        json_prefill="{",
    )
    meta = dict(meta or {})
    if meta.get("bedrock_latency_ms") is None:
        meta["bedrock_latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
    # Só métricas/flags — sem texto do modelo.
    meta["qualidade"] = _avaliar_qualidade_estrutural(parsed if isinstance(parsed, dict) else {})
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico de prompt do wizard")
    parser.add_argument(
        "--cenario",
        choices=["curto", "medio", "longo", "todos"],
        default="todos",
        help="Qual cenário avaliar (padrão: todos)",
    )
    parser.add_argument(
        "--invoke-bedrock",
        action="store_true",
        help="Opcional: chama Bedrock de verdade (requer AWS configurada)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite resumo JSON (apenas métricas numéricas / IDs)",
    )
    args = parser.parse_args()

    nomes = list(CENARIOS) if args.cenario == "todos" else [args.cenario]
    _info_max_tokens()

    resumo = []
    for nome in nomes:
        montado = _montar_cenario(CENARIOS[nome]())
        usage = None
        if args.invoke_bedrock:
            try:
                usage = _invoke_opcional(montado)
            except Exception as exc:
                print(
                    f"\n[aviso] falha ao invocar Bedrock no cenário {nome}: {exc}",
                    file=sys.stderr,
                )
                usage = None
        _imprimir_cenario(montado, usage=usage)
        p = montado["partes"]
        top = montado["ranking"]
        item = {
            "cenario": nome,
            "system_chars": p["system_total_chars"],
            "catalogo_chars": p["system_catalogo_chars"],
            "ancoras_chars": p["system_ancoras_chars"],
            "ancoras_count": p["ancoras_count"],
            "diretrizes_chars": p["system_diretrizes_chars"],
            "user_chars": p["user_content_chars"],
            "matcher_top_ids": [r.get("id") for r in top],
            "matcher_top_scores": [int(r.get("score") or 0) for r in top],
        }
        if usage:
            item["input_tokens"] = usage.get("input_tokens")
            item["output_tokens"] = usage.get("output_tokens")
            item["bedrock_latency_ms"] = usage.get("bedrock_latency_ms")
        resumo.append(item)

    if args.json:
        print("\n" + json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
