import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime

import psycopg2.extras
from langchain_aws import ChatBedrock

from sprint_governance import (
    GENESE_KANBAN_MAX,
    STAT_EM_ANDAMENTO,
    STAT_PLANEJADA_BACKLOG,
    status_genese_kanban,
)
from sprint_squad import (
    atualizar_nome_squad_pos_sprint,
    criar_squad_vazia_para_sprint,
    resolver_ou_criar_projeto_ctdi,
)
try:
    from ai_engine.vitrine_tags import classify_vitrine_tags
except ImportError:
    from vitrine_tags import classify_vitrine_tags

logger = logging.getLogger(__name__)

# Marcador de versão — confirme este texto nos logs do worker após deploy/restart
KANBAN_ENGINE_VERSION = "v3-governanca-max12-ondas"
logger.info("Motor Kanban %s carregado.", KANBAN_ENGINE_VERSION)

# Imports resilientes: worker (ai_engine.*), app.py ou execução direta do script
_ai_engine_dir = os.path.dirname(os.path.abspath(__file__))
_sysf_dir = os.path.dirname(_ai_engine_dir)
for _path in (_sysf_dir, _ai_engine_dir):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    from ai_engine.s3_helper import upload_to_s3
    from ai_engine.pdf_generator import gerar_pdf_final
except ImportError:
    from s3_helper import upload_to_s3
    from pdf_generator import gerar_pdf_final


def _extrair_json_da_resposta(texto):
    """Extrai objeto JSON da resposta do modelo (cercas markdown ou recorte {…})."""
    if texto is None:
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
            return json.loads(limpo[inicio: fim + 1])
        raise


class LeActionAIProcessor:
    def __init__(self, db_manager):
        self.db = db_manager
        self.llm = ChatBedrock(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 8192,
            },
        )

    def extrair_diretrizes_contexto(self, maturity):
        diretrizes = []

        sede = maturity.get("localizacao_sede") or "Não informada"
        alunos = maturity.get("qtd_alunos") or 0
        e_rede = maturity.get("rede_ensino") in [True, 1, "true", "True"]
        tipo = maturity.get("tipo_ensino") or "K12"
        cidade = maturity.get("cidade_clie") or ""
        bairro = maturity.get("bairro_clie") or ""

        if tipo == "K12":
            diretrizes.append(
                "- SEGMENTO: Educação Básica (K12). Foco em BNCC, PNED e segurança digital para menores."
            )
        elif tipo == "Superior":
            diretrizes.append(
                "- SEGMENTO: Ensino Superior. Foco em LMS robusto, retenção de alunos e preparação para o mercado."
            )
        elif tipo == "Tecnico":
            diretrizes.append(
                "- SEGMENTO: Ensino Técnico/Profissionalizante. Foco em laboratórios virtuais e simulações práticas."
            )
        elif tipo == "Idiomas/Cursos Livres":
            diretrizes.append(
                "- SEGMENTO: Idiomas/Cursos Livres. Foco em experiência do cliente (UX) e conversão digital."
            )
        elif tipo == "Educação Corporativa":
            diretrizes.append(
                "- SEGMENTO: Educação Corporativa. Foco em microlearning e desenvolvimento de competências (SKAs)."
            )

        diretrizes.append(f"- LOCALIZAÇÃO (SEDE): {sede}")
        if bairro or cidade:
            diretrizes.append(f"- BAIRRO/CIDADE: {bairro or '—'} / {cidade or '—'}")
        diretrizes.append(f"- PORTE: {alunos} alunos.")
        diretrizes.append(f"- ESTRUTURA: {'Unidade de Rede' if e_rede else 'Unidade Independente'}")

        mercado = (maturity.get("dados_mercado") or "").strip()
        etno = (maturity.get("dados_etnograficos") or "").strip()
        clima = (maturity.get("clima_organizacional") or "").strip()
        if mercado:
            diretrizes.append(f"- CONTEXTO DE MERCADO (gestor): {mercado[:1200]}")
        if etno:
            diretrizes.append(f"- PERFIL DA COMUNIDADE (gestor): {etno[:1200]}")
        if clima:
            diretrizes.append(f"- CLIMA ORGANIZACIONAL (gestor): {clima[:1200]}")

        mod_mercado = (maturity.get("moderacao_dados_mercado") or "").strip()
        mod_etno = (maturity.get("moderacao_dados_etnograficos") or "").strip()
        mod_clima = (maturity.get("moderacao_clima_organizacional") or "").strip()
        if mod_mercado:
            diretrizes.append(f"- INSIGHT MODERADOR (mercado): {mod_mercado[:800]}")
        if mod_etno:
            diretrizes.append(f"- INSIGHT MODERADOR (comunidade): {mod_etno[:800]}")
        if mod_clima:
            diretrizes.append(f"- INSIGHT MODERADOR (clima): {mod_clima[:800]}")

        return "\n".join(diretrizes)

    def obter_rubricas(self, cur, id_matu):
        """Recupera rubricas do PRESENTE, vetores estratégicos e insights da Bússola."""
        try:
            query = """
                    SELECT q.id_ques,
                           q.desc_ques,
                           rub.label_rubr,
                           rub.desc_rubr,
                           d.name_doma,
                           d.vetor_estrategico,
                           b.insight_chave
                    FROM ctdi_surv s
                             JOIN ctdi_quest q ON s.id_ques = q.id_ques
                             JOIN public.leaf_doma d ON q.id_doma = d.id_doma
                             JOIN ctdi_rubricas rub ON (s.id_ques = rub.id_ques AND s.grad_ques = rub.grad_rubr)
                             LEFT JOIN ctdi_bussola b ON q.id_ques = b.id_ques
                    WHERE s.id_matu = %s
                      AND q.prefu_ques = 'P'
                    ORDER BY q.id_doma, q.id_ques;
                    """
            cur.execute(query, (id_matu,))
            respostas = cur.fetchall()

            if not respostas:
                return "Rubricas estratégicas não encontradas."

            output = "\n--- STATUS QUALITATIVO DOS 9 DOMÍNIOS (BÚSSOLA) ---\n"
            for r in respostas:
                output += f"DOMÍNIO: {r['name_doma']} | VETOR: {r['vetor_estrategico']}\n"
                output += f"STATUS ATUAL: {r['label_rubr']} - {r['desc_rubr']}\n"
                if r["insight_chave"]:
                    output += f"INSIGHT LEACTION (BÚSSOLA): {r['insight_chave']}\n"
                else:
                    output += "INSIGHT LEACTION (BÚSSOLA): Analisar gap técnico conforme vetor.\n"
                output += "-" * 30 + "\n"

            return output

        except Exception as e:
            print(f"❌ [ERRO] Falha ao obter_rubricas: {e}")
            return "Erro técnico ao recuperar detalhes das respostas."

    def obter_catalogo_blocos_gaps(self, cur, lista_dominios, pdom_gap):
        """Catálogo completo de blocos candidatos (domínios com gap > 0) para a IA priorizar."""
        if not lista_dominios:
            return "Nenhum domínio com gap identificado.", {}

        try:
            query = """
                    SELECT b.id_bloc,
                           b.name_bloc,
                           b.desc_bloc,
                           d.name_doma,
                           d.id_doma,
                           CAST(dim.id_dime AS INTEGER) AS dime_num
                    FROM leaf_bloc b
                             JOIN leaf_doma d ON b.id_doma = d.id_doma
                             JOIN leaf_dime dim ON b.id_dime = dim.id_dime
                    WHERE b.id_doma::text = ANY (%s)
                    ORDER BY array_position(%s, b.id_doma::text),
                             dime_num ASC,
                             b.id_bloc ASC;
                    """
            cur.execute(query, (lista_dominios, lista_dominios))
            blocos = cur.fetchall()

            blocos_map = {}
            output = (
                "\n--- CATÁLOGO DE BLOCOS CANDIDATOS (use id_bloco exato na resposta JSON) ---\n"
                "IMPORTANTE: NÃO selecione todos. Escolha apenas os mais críticos.\n"
            )
            for b in blocos:
                dom_key = str(b["id_doma"])
                gap = float(pdom_gap.get(dom_key) or pdom_gap.get(b["id_doma"]) or 0)
                blocos_map[b["id_bloc"]] = b
                output += (
                    f"ID_BLOCO={b['id_bloc']} | {b['name_bloc']} | "
                    f"Domínio: {b['name_doma']} (gap {gap:.1f}%) | Dimensão {b['dime_num']}\n"
                )
                if b.get("desc_bloc"):
                    desc_curta = str(b["desc_bloc"]).replace("\n", " ")[:180]
                    output += f"  → {desc_curta}\n"

            return output, blocos_map

        except Exception as e:
            print(f"❌ [ERRO] obter_catalogo_blocos_gaps: {e}")
            return f"Erro ao mapear blocos: {e}", {}

    @staticmethod
    def _parse_id_bloco(item):
        if not isinstance(item, dict):
            return None
        for key in ("id_bloco", "id_bloc", "ID_BLOCO"):
            raw = item.get(key)
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _parse_objetivo_id(item):
        if not isinstance(item, dict):
            return None
        for key in ("id_objetivo", "objetivo_id", "ID_OBJETIVO"):
            raw = item.get(key)
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _justificativa_estrategica(item):
        return (
            item.get("justificativa_baseada_no_relatorio")
            or item.get("justificativa_priorizacao")
            or ""
        )

    @staticmethod
    def _justificativa_tatica(item, plano_tatico=None):
        plano_tatico = plano_tatico or {}
        return (
            item.get("como_resolve_o_problema_declarado")
            or item.get("como_resolve_a_dor")
            or plano_tatico.get("problema_analisado")
            or ""
        )

    @staticmethod
    def _campo_contexto_prompt(val):
        """Normaliza campos de contexto local para o prompt (evita None no template)."""
        if val is None:
            return "Não informado"
        texto = str(val).strip()
        return texto if texto else "Não informado"

    def _montar_prompt_estrategico(
        self,
        maturity,
        timestamp_geracao,
        contexto_raw,
        detalhamento_gaps,
        rubricas_vivas,
        catalogo_blocos,
        problema_declarado,
        catalogo_objetivos="",
    ):
        bairro_clie = self._campo_contexto_prompt(maturity.get("bairro_clie"))
        cidade_clie = self._campo_contexto_prompt(maturity.get("cidade_clie"))
        estado_clie = self._campo_contexto_prompt(maturity.get("estado_clie"))
        dados_etnograficos = self._campo_contexto_prompt(maturity.get("dados_etnograficos"))
        dados_mercado = self._campo_contexto_prompt(maturity.get("dados_mercado"))
        gap_global = float(maturity.get("pgen_gap") or 0.0)
        problema_txt = (problema_declarado or "Não informado pelo cliente").strip()

        return f"""
Você é o Agente Master da LeAction — um CTO / Consultor Educacional Sênior.
Sua missão NÃO é listar todas as fragilidades do assessment (162 questões).
Você deve PRIORIZAR como um estrategista executivo: cruzar a matriz de respostas,
o relatório de BI (gaps e Bússola) e o contexto mercadológico da unidade para escolher apenas as batalhas mais importantes.

╔══════════════════════════════════════════════════════════════╗
║ REGRA ABSOLUTA DE GROUNDING (ATERRAMENTO OBRIGATÓRIO)        ║
╠══════════════════════════════════════════════════════════════╣
║ REGRA ABSOLUTA: VOCÊ NÃO PODE RECOMENDAR UM BLOCO PARA O     ║
║ ROADMAP OU PLANO TÁTICO SE ELE NÃO TIVER FORTE CONEXÃO COM AS  ║
║ VULNERABILIDADES DESCRITAS NO RELATÓRIO DE INTELIGÊNCIA QUE    ║
║ VOCÊ ACABOU DE CRIAR — CRUZADO COM OS GAPS REAIS DO BI E O     ║
║ CONTEXTO INSTITUCIONAL E DE MERCADO DA UNIDADE.              ║
╚══════════════════════════════════════════════════════════════╝

CADEIA DE PENSAMENTO OBRIGATÓRIA (antes de selecionar qualquer sprint):
1. PRIMEIRO: redija integralmente relatorio_inteligencia (síntese, 9 domínios,
   análise regional e próximos passos) com base nos gaps numéricos, Bússola e contexto.
2. DEPOIS: selecione blocos SOMENTE a partir das vulnerabilidades que você documentou
   no relatório — cite explicitamente domínio, % de gap, insight da Bússola e trecho
   do relatório que embasa cada escolha.
3. Para sprints táticas: cruze obrigatoriamente o Problema Declarado com gaps/rubricas
   do bloco escolhido e explique o encadeamento causa → solução.

══════════════════════════════════════════════════════════════
🎯 PROBLEMA DECLARADO PELO CLIENTE (DOR ATUAL — PRIORIDADE MÁXIMA)
══════════════════════════════════════════════════════════════
"{problema_txt}"

Vasculhe o assessment em busca de fragilidades que CAUSAM ou AMPLIFICAM essa dor.
No plano tático, indique exatamente 3 sprints (blocos) onde o cliente foi mal avaliado
e que atacam diretamente essa dor — sempre citando gap, Bússola e relatório.

══════════════════════════════════════════════════════════════
DADOS DO SISTEMA (FONTE DE VERDADE — BI E CONTEXTO LOCAL)
══════════════════════════════════════════════════════════════
Gerado em: {timestamp_geracao}
Perfil institucional geral:
{contexto_raw}

CONTEXTO LOCAL E MERCADOLÓGICO:
Localização: {bairro_clie}, {cidade_clie} - {estado_clie}
Perfil Etnográfico e da Comunidade: {dados_etnograficos}
Realidade de Mercado e Concorrência: {dados_mercado}

Gap global de transformação: {gap_global:.2f}
Gaps por domínio (use estes números nas justificativas):
{detalhamento_gaps}

Relatório qualitativo (Bússola — 9 domínios — cite insights por nome):
{rubricas_vivas}

Catálogo de blocos candidatos (domínios com gap > 0 — use id_bloco exato):
{catalogo_blocos}
{catalogo_objetivos}

══════════════════════════════════════════════════════════════
DIRETRIZES DE PRIORIZAÇÃO EXECUTIVA
══════════════════════════════════════════════════════════════
1. NÃO crie ações para todos os gaps. Seja seletivo e estratégico.
2. Cada sprint DEVE provar aterramento: gap real + insight Bússola + trecho do relatório + contexto da unidade.
3. roadmap_estrategico: NO MÁXIMO 10 blocos — os mais críticos (gap > 0) com conexão indiscutível ao relatório.
4. plano_tatico_problema.sprints_resolucao: EXATAMENTE 3 blocos ligados ao Problema Declarado.
5. Use SOMENTE id_bloco existentes no catálogo. Não invente IDs nem nomes de blocos.
6. relatorio_inteligencia deve analisar os 9 domínios com densidade (use insights da Bússola).
7. DIRETRIZ DE PERSONALIZAÇÃO ESTRITA: Você DEVE correlacionar os gaps identificados com a Realidade de Mercado e o Perfil Etnográfico. As sugestões de ações, o tom e a viabilidade das prioridades devem ser moldadas para funcionar especificamente no bairro/região informada.

══════════════════════════════════════════════════════════════
FORMATO DE SAÍDA — APENAS JSON VÁLIDO (sem markdown, sem texto extra)
══════════════════════════════════════════════════════════════
{{
  "relatorio_inteligencia": {{
    "sintese_executiva": "Gap global, contexto da unidade e vulnerabilidades críticas identificadas",
    "analise_dominios": "Análise nominal dos 9 domínios citando label_rubr, gap % e insight Bússola",
    "analise_regional": "Impacto direto da localização ({bairro_clie}, {cidade_clie}), do perfil etnográfico da comunidade e da pressão da concorrência no mercado local sobre os resultados do assessment.",
    "proximos_passos_90_dias": "Ações preparatórias alinhadas ao roadmap priorizado"
  }},
  "roadmap_estrategico": [
    {{
      "id_bloco": 123,
      "id_objetivo": 1,
      "nome_sprint": "Nome executivo da sprint",
      "tags": ["formacao"],
      "justificativa_baseada_no_relatorio": "OBRIGATÓRIO: cite id_objetivo + domínio + gap % + insight Bússola + impacto no objetivo canônico + trecho do relatório."
    }}
  ],
  "plano_tatico_problema": {{
    "problema_analisado": "Resumo da dor declarada cruzada com gaps/rubricas do assessment",
    "sprints_resolucao": [
      {{
        "id_bloco": 456,
        "id_objetivo": 2,
        "nome_sprint": "Nome da sprint tática",
        "tags": ["software"],
        "como_resolve_o_problema_declarado": "OBRIGATÓRIO: cruze id_objetivo + dor + gap + insight Bússola + encadeamento causa → solução."
      }}
    ]
  }}
}}

REGRAS FINAIS:
- roadmap_estrategico: array com NO MÁXIMO 10 itens — cada um com id_objetivo válido da matriz canônica.
- sprints_resolucao: array com EXATAMENTE 3 itens — cada um com id_objetivo válido.
- tags: array com 1–2 valores em {{formacao, equipamentos, software}} — classifica a necessidade da sprint para a vitrine ActionHub (IA só na criação; sem reclassificar depois).
- justificativa_baseada_no_relatorio e como_resolve_o_problema_declarado são OBRIGATÓRIAS e não podem ser genéricas.
- Evite repetir o mesmo id_bloco entre roadmap_estrategico e sprints_resolucao.
- Retorne SOMENTE o JSON.
"""

    @staticmethod
    def _markdown_from_plano(plano_json, timestamp_geracao):
        rel = plano_json.get("relatorio_inteligencia") or {}
        roadmap = plano_json.get("roadmap_estrategico") or []
        tatico = plano_json.get("plano_tatico_problema") or {}
        sprints_taticas = tatico.get("sprints_resolucao") or []

        linhas_roadmap = []
        for i, item in enumerate(roadmap, 1):
            linhas_roadmap.append(
                f"{i}. **{item.get('nome_sprint', 'Sprint')}** (Bloco {item.get('id_bloco', '?')})\n"
                f"   - {LeActionAIProcessor._justificativa_estrategica(item)}"
            )

        linhas_tatico = []
        for i, item in enumerate(sprints_taticas, 1):
            linhas_tatico.append(
                f"{i}. **[TÁTICO] {item.get('nome_sprint', 'Sprint')}** (Bloco {item.get('id_bloco', '?')})\n"
                f"   - {LeActionAIProcessor._justificativa_tatica(item, tatico)}"
            )

        return f"""[INICIO_VISAO_EXECUTIVA]
## Síntese Executiva
Relatório Gerado em {timestamp_geracao}

{rel.get('sintese_executiva', '')}
[FIM_VISAO_EXECUTIVA]

[INICIO_ANALISE_DOMINIOS]
## Diagnóstico dos Domínios

{rel.get('analise_dominios', '')}
[FIM_ANALISE_DOMINIOS]

[INICIO_PLANO_TATICO]
## Plano Tático — Problema Declarado

**Dor analisada:** {tatico.get('problema_analisado', '')}

{chr(10).join(linhas_tatico) if linhas_tatico else '_Nenhuma sprint tática priorizada._'}
[FIM_PLANO_TATICO]

[INICIO_ROADMAP_ESTRATEGICO]
## Roadmap Estratégico (Core — máx. 10 sprints)

{chr(10).join(linhas_roadmap) if linhas_roadmap else '_Nenhuma sprint estratégica priorizada._'}
[FIM_ROADMAP_ESTRATEGICO]

[INICIO_ANALISE_REGIONAL]
## Análise Geográfica & Regional

{rel.get('analise_regional', '')}
[FIM_ANALISE_REGIONAL]

[INICIO_PROXIMOS_PASSOS]
## Próximos Passos (90 Dias)

{rel.get('proximos_passos_90_dias', '')}
[FIM_PROXIMOS_PASSOS]
"""

    def _garantir_ctdi_main(self, cur, id_matu):
        cur.execute("SELECT id_ctdi FROM ctdi_main WHERE id_matu = %s LIMIT 1", (id_matu,))
        res = cur.fetchone()
        if res:
            return res[0]
        cur.execute(
            """
            INSERT INTO ctdi_main (id_matu, id_dime, name_ctdi, stat_ctdi)
            VALUES (%s, 1, 'Plano de Transformação Digital', 'ativo')
            RETURNING id_ctdi
            """,
            (id_matu,),
        )
        return cur.fetchone()[0]

    def _inserir_sprint_kanban(
        self, cur, id_ctdi, id_itera, id_bloc, bloco_info, nome_sprn, desc_sprn, ordr, status, tatico=False,
        objetivo_id=None,
        ai_tags=None,
    ):
        id_dim = bloco_info.get("dime_num", 1) if bloco_info else 1
        nome_bloc = (bloco_info or {}).get("name_bloc", nome_sprn)
        prefixo = "[TÁTICO] " if tatico else ""
        nome_final = f"{prefixo}[DIM {id_dim}] {nome_sprn or nome_bloc}"

        id_proj = resolver_ou_criar_projeto_ctdi(cur, id_ctdi)
        id_squad_novo = criar_squad_vazia_para_sprint(
            cur, id_proj=id_proj, nome_sprint=nome_final
        )

        tags = classify_vitrine_tags(
            nome_sprint=nome_sprn or nome_bloc,
            desc_sprint=desc_sprn,
            name_bloc=(bloco_info or {}).get("name_bloc"),
            name_doma=(bloco_info or {}).get("name_doma"),
            dime_num=id_dim,
            ai_tags=ai_tags,
            tatico=tatico,
        )

        # Garante coluna tags (idempotente) antes do INSERT — bases pré-026
        try:
            cur.execute(
                "ALTER TABLE public.ctdi_sprn ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}'"
            )
        except Exception:
            pass

        cur.execute(
            """
            INSERT INTO ctdi_sprn (
                id_itera, id_bloc, name_sprn, desc_sprn, stat_sprn, ordr_sprn, id_squad, objetivo_id, tags
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_sprn
            """,
            (id_itera, id_bloc, nome_final, desc_sprn, status, ordr, id_squad_novo, objetivo_id, tags),
        )
        id_sprn = cur.fetchone()[0]
        if isinstance(id_sprn, dict):
            id_sprn = id_sprn.get("id_sprn")
        atualizar_nome_squad_pos_sprint(cur, id_squad_novo, nome_final, int(id_sprn))
        url_k = f"https://leaction.sys/kanban/{id_sprn}"
        cur.execute("UPDATE ctdi_sprn SET url_kanban = %s WHERE id_sprn = %s", (url_k, id_sprn))
        return id_sprn

    @staticmethod
    def _coletar_entradas_plano(plano_json):
        """Coleta sprints táticas + estratégicas do JSON da IA (sem limite de inserção)."""
        if not isinstance(plano_json, dict):
            raise ValueError("JSON da IA não é um objeto.")

        plano_tatico = plano_json.get("plano_tatico_problema") or {}
        if not isinstance(plano_tatico, dict):
            plano_tatico = {}

        sprints_taticas = plano_tatico.get("sprints_resolucao") or []
        sprints_estrategicas = plano_json.get("roadmap_estrategico") or []

        if not isinstance(sprints_taticas, list):
            sprints_taticas = []
        if not isinstance(sprints_estrategicas, list):
            sprints_estrategicas = []

        entradas = []
        ids_vistos = set()

        for item in sprints_taticas:
            id_b = LeActionAIProcessor._parse_id_bloco(item)
            if id_b is None or id_b in ids_vistos:
                continue
            ids_vistos.add(id_b)
            entradas.append({"tipo": "tatico", "item": item, "id_bloco": id_b})

        for item in sprints_estrategicas:
            id_b = LeActionAIProcessor._parse_id_bloco(item)
            if id_b is None or id_b in ids_vistos:
                continue
            ids_vistos.add(id_b)
            entradas.append({"tipo": "estrategico", "item": item, "id_bloco": id_b})

        return entradas, plano_tatico

    @staticmethod
    def _serializar_sprint_reserva(entrada, bloco, plano_tatico):
        item = entrada["item"]
        if entrada["tipo"] == "tatico":
            desc = LeActionAIProcessor._justificativa_tatica(item, plano_tatico)
        else:
            desc = LeActionAIProcessor._justificativa_estrategica(item)
        return {
            "tipo": entrada["tipo"],
            "id_bloco": entrada["id_bloco"],
            "nome_sprint": item.get("nome_sprint") or (bloco or {}).get("name_bloc"),
            "nome_bloco": (bloco or {}).get("name_bloc"),
            "justificativa": desc,
            "origem": "genese_ia_master_reserva",
        }

    @staticmethod
    def _extrair_sprints_priorizadas(plano_json):
        """Divide o plano: até 12 no Kanban; excedentes → backlog geral do relatório."""
        entradas, plano_tatico = LeActionAIProcessor._coletar_entradas_plano(plano_json)
        kanban = entradas[:GENESE_KANBAN_MAX]
        reserva = entradas[GENESE_KANBAN_MAX:]
        return kanban, reserva, plano_tatico

    def _obter_info_bloco(self, cur, id_bloc):
        cur.execute(
            """
            SELECT b.id_bloc,
                   b.name_bloc,
                   b.desc_bloc,
                   d.name_doma,
                   d.id_doma,
                   CAST(dim.id_dime AS INTEGER) AS dime_num
            FROM leaf_bloc b
                     JOIN leaf_doma d ON b.id_doma = d.id_doma
                     JOIN leaf_dime dim ON b.id_dime = dim.id_dime
            WHERE b.id_bloc = %s
            LIMIT 1
            """,
            (id_bloc,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def _limpar_kanban_ctdi(self, cur, id_ctdi):
        """Remove todas as sprints e ondas do CTDI antes de reinserir o backlog priorizado."""
        cur.execute(
            """
            DELETE FROM ctdi_sprn
            WHERE id_itera IN (SELECT id_itera FROM ctdi_itera WHERE id_ctdi = %s)
            """,
            (id_ctdi,),
        )
        cur.execute("DELETE FROM ctdi_itera WHERE id_ctdi = %s", (id_ctdi,))

    def popular_kanban_priorizado(self, cur, id_matu, plano_json):
        """
        Insere no Kanban até 12 sprints da IA Master:
        - índices 0–2 (Onda 1): em_andamento
        - índices 3–11 (Ondas 2–4): planejada_backlog
        Excedentes ficam em plano_json['backlog_geral_relatorio'] (não entram em ctdi_sprn).
        """
        sprints_kanban, sprints_reserva, plano_tatico = self._extrair_sprints_priorizadas(plano_json)

        reserva_serializada = []
        for entrada in sprints_reserva:
            bloco = self._obter_info_bloco(cur, entrada["id_bloco"])
            if bloco:
                reserva_serializada.append(
                    self._serializar_sprint_reserva(entrada, bloco, plano_tatico)
                )

        if reserva_serializada:
            plano_json["backlog_geral_relatorio"] = reserva_serializada
        elif "backlog_geral_relatorio" in plano_json:
            plano_json.pop("backlog_geral_relatorio", None)

        logger.info(
            "[KANBAN] id_matu=%s | kanban=%d (máx. %d) | reserva_backlog=%d",
            id_matu,
            len(sprints_kanban),
            GENESE_KANBAN_MAX,
            len(reserva_serializada),
        )

        id_ctdi = self._garantir_ctdi_main(cur, id_matu)
        self._limpar_kanban_ctdi(cur, id_ctdi)

        if not sprints_kanban:
            logger.warning(
                "[KANBAN] id_matu=%s | Nenhuma sprint válida no JSON — Kanban zerado.",
                id_matu,
            )
            return 0

        ordr_global = 1
        inseridas = 0
        id_itera_tatico = None
        id_itera_estrategico = None
        idx_onda_estrategica = 0
        contador_estrategico_na_onda = 0

        for idx_kanban, entrada in enumerate(sprints_kanban):
            id_b = entrada["id_bloco"]
            item = entrada["item"]
            bloco = self._obter_info_bloco(cur, id_b)
            if not bloco:
                logger.warning("[KANBAN] id_bloco=%s ignorado — bloco inexistente em leaf_bloc.", id_b)
                continue

            status_kanban = status_genese_kanban(idx_kanban)
            objetivo_id = self._parse_objetivo_id(item)

            if entrada["tipo"] == "tatico":
                if id_itera_tatico is None:
                    cur.execute(
                        """
                        INSERT INTO ctdi_itera (id_ctdi, id_phase, name_itera, stat_itera)
                        VALUES (%s, 1, %s, %s)
                        RETURNING id_itera
                        """,
                        (id_ctdi, "Alvo Tático — Problema Declarado", STAT_EM_ANDAMENTO),
                    )
                    id_itera_tatico = cur.fetchone()[0]

                self._inserir_sprint_kanban(
                    cur,
                    id_ctdi,
                    id_itera_tatico,
                    id_b,
                    bloco,
                    item.get("nome_sprint") or bloco["name_bloc"],
                    self._justificativa_tatica(item, plano_tatico),
                    ordr_global,
                    status_kanban,
                    tatico=True,
                    objetivo_id=objetivo_id,
                    ai_tags=item.get("tags") or item.get("vitrine_categories"),
                )
            else:
                if id_itera_estrategico is None or contador_estrategico_na_onda >= 3:
                    idx_onda_estrategica += 1
                    fase = idx_onda_estrategica + (1 if id_itera_tatico else 0)
                    status_itera = STAT_PLANEJADA_BACKLOG if idx_kanban >= 3 else STAT_EM_ANDAMENTO
                    cur.execute(
                        """
                        INSERT INTO ctdi_itera (id_ctdi, id_phase, name_itera, stat_itera)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id_itera
                        """,
                        (id_ctdi, fase, f"Onda {idx_onda_estrategica} — Core Roadmap", status_itera),
                    )
                    id_itera_estrategico = cur.fetchone()[0]
                    contador_estrategico_na_onda = 0

                self._inserir_sprint_kanban(
                    cur,
                    id_ctdi,
                    id_itera_estrategico,
                    id_b,
                    bloco,
                    item.get("nome_sprint") or bloco["name_bloc"],
                    self._justificativa_estrategica(item),
                    ordr_global,
                    status_kanban,
                    tatico=False,
                    objetivo_id=objetivo_id,
                    ai_tags=item.get("tags") or item.get("vitrine_categories"),
                )
                contador_estrategico_na_onda += 1

            ordr_global += 1
            inseridas += 1

        logger.info("[KANBAN] id_matu=%s | %d sprint(s) inserida(s) no Kanban.", id_matu, inseridas)
        return inseridas

    def processar_diagnostico(self, conn, id_matu):
        try:
            agora = datetime.now()
            timestamp_geracao = agora.strftime("%d/%m/%Y %H:%M:%S")
            print(
                f"--- [Master {KANBAN_ENGINE_VERSION}] id_matu={id_matu} | "
                f"Diagnóstico Priorizado em {timestamp_geracao}...",
                flush=True,
            )

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT m.*,
                           c.nome_clie,
                           c.mail_clie,
                           c.localizacao_sede,
                           c.cidade_clie,
                           c.bairro_clie,
                           c.estado_clie,
                           c.qtd_alunos,
                           c.qtd_colaboradores,
                           c.rede_ensino,
                           c.tipo_ensino,
                           c.dados_mercado,
                           c.dados_etnograficos,
                           c.clima_organizacional,
                           c.moderacao_dados_mercado,
                           c.moderacao_dados_etnograficos,
                           c.moderacao_clima_organizacional
                    FROM ctdi_matu m
                             JOIN ctdi_clie c ON m.id_clie = c.id_clie
                    WHERE m.id_matu = %s
                    """,
                    (id_matu,),
                )
                maturity = cur.fetchone()

                if not maturity:
                    print(f"--- [ERRO] Registro id_matu {id_matu} não encontrado.")
                    return False

                maturity["nome_clie_text"] = maturity.get("nome_clie")
                maturity["mail_clie_text"] = maturity.get("mail_clie") or "Não informado"
                maturity["pgen_presente"] = float(maturity.get("pgen_pres") or 0.0)
                maturity["pgen_futuro"] = float(maturity.get("pgen_fut") or 0.0)
                maturity["pgen_gap"] = float(maturity.get("pgen_gap") or 0.0)

                pdom_gap = maturity.get("pdom_gap") or {}
                detalhamento_gaps = "\n".join(
                    [f"- Domínio {d}: Gap de {v}%" for d, v in pdom_gap.items()]
                )

                pdom_sect_gap = maturity.get("pdom_sect_gap") or {}
                fila_1 = sorted(
                    [(d, float(v)) for d, v in pdom_sect_gap.items() if float(v) > 0],
                    key=lambda x: x[1],
                    reverse=True,
                )
                dom_prior_setor = [d[0] for d in fila_1]
                fila_2 = sorted(
                    [
                        (d, float(v))
                        for d, v in pdom_gap.items()
                        if d not in dom_prior_setor and float(v) > 0
                    ],
                    key=lambda x: x[1],
                    reverse=True,
                )
                lista_final_prioridade = dom_prior_setor + [d[0] for d in fila_2]

                problema_declarado = (
                    maturity.get("clima_organizacional") or "Não informado pelo cliente"
                ).strip()

                contexto_raw = self.extrair_diretrizes_contexto(maturity)
                rubricas_vivas = self.obter_rubricas(cur, id_matu)
                catalogo_blocos, blocos_map = self.obter_catalogo_blocos_gaps(
                    cur, lista_final_prioridade, pdom_gap
                )
                from estrategia_matriz import (
                    carregar_arvore_matriz_okr,
                    formatar_catalogo_objetivos_prompt,
                )

                arvore_okr = carregar_arvore_matriz_okr(conn)
                catalogo_objetivos = formatar_catalogo_objetivos_prompt(arvore_okr)

            prompt = self._montar_prompt_estrategico(
                maturity,
                timestamp_geracao,
                contexto_raw,
                detalhamento_gaps,
                rubricas_vivas,
                catalogo_blocos,
                problema_declarado,
                catalogo_objetivos=catalogo_objetivos,
            )

            resposta = self.llm.invoke(prompt)
            try:
                plano_json = _extrair_json_da_resposta(resposta.content)
                sprints_kanban, _, _ = self._extrair_sprints_priorizadas(plano_json)
                logger.info(
                    "[IA] id_matu=%s | JSON válido | sprints kanban=%d",
                    id_matu,
                    len(sprints_kanban),
                )
            except (json.JSONDecodeError, ValueError, TypeError) as parse_err:
                logger.error(
                    "[IA] Falha ao extrair/validar JSON da IA para id_matu=%s: %s",
                    id_matu,
                    parse_err,
                    exc_info=True,
                )
                return False

            texto_markdown = self._markdown_from_plano(plano_json, timestamp_geracao)

            path_pdf = gerar_pdf_final(maturity, texto_markdown)
            url_s3 = upload_to_s3(path_pdf, id_matu, maturity.get("id_surv", 0))

            with conn.cursor() as cur:
                self.popular_kanban_priorizado(cur, id_matu, plano_json)

                cur.execute(
                    """
                    UPDATE ctdi_matu
                    SET txt_diagnostico_ia     = %s,
                        url_pdf_ia             = %s,
                        json_plano_estrategico = %s,
                        status_ia              = 'CONCLUIDO',
                        dt_fim_ia              = %s
                    WHERE id_matu = %s
                    """,
                    (
                        texto_markdown,
                        url_s3,
                        psycopg2.extras.Json(plano_json),
                        agora,
                        id_matu,
                    ),
                )
                conn.commit()

            if os.path.exists(path_pdf):
                os.remove(path_pdf)
            return True

        except Exception as exc:
            logger.error(
                "[IA] Erro inesperado no diagnóstico id_matu=%s: %s",
                id_matu,
                exc,
                exc_info=True,
            )
            traceback.print_exc()
            return False
