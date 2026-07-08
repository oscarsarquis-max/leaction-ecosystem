"""Estúdio de Criação/Ingestão — catálogo universal + 5ª dimensão setorial via IA."""

from __future__ import annotations

import copy
import json
import logging
import re
import unicodedata
from typing import Any

from app.core.framework_definitions import (
    CANONICAL_DOMAIN_KEYS,
    DOMAIN_NAMES_BY_KEY,
    OPERATIONAL_DOMAINS,
    SECTOR_DIMENSION_TEMPLATE_KEY,
    get_framework_taxonomy_for_prompt,
    is_valid_operational_domain_key,
    normalize_domain_key,
)
from app.core.tenant_framework_resolver import relink_orphan_lead_tenants
from app.data.legacy_framework_loader import build_full_methodology_document
from app.data.legacy_quest_loader import load_universal_assessment_items, universal_dimensions_summary
from app.data.maturity_defaults import DEFAULT_MATURITY_LEVELS
from app.database.models import AssessmentItem, Framework, MaturityLevel, db
from app.data.rubric_patterns import (
    PANELDX_FUTURO_GENERIC_DESC,
    PANELDX_PRESENTE_GENERIC_DESC,
    default_futuro_options,
    default_maturity_options,
    normalize_question_options,
    normalize_rubric_options,
    normalize_sector_question_options,
)
from app.core.dev_users import DEV_FRAMEWORK_ID
from app.core.sector_constants import (
    is_canonical_education_framework,
    is_canonical_education_sector,
)
from app.core.education_framework_seeder import ensure_education_framework
from app.infrastructure.ai_client import invoke_claude
from app.infrastructure.web_search import normalize_sector_name, search_sector_references
from app.services.framework_taxonomy_service import (
    ensure_framework_taxonomy,
    get_framework_taxonomy,
    import_taxonomy_from_legacy,
    import_taxonomy_from_methodology_document,
)

logger = logging.getLogger(__name__)

UNIVERSAL_DIMENSIONS = [
    {"key": "sv", "name": "Shared Vision", "label": "Estratégia"},
    {"key": "hc", "name": "Heart Connection", "label": "Humano e Cultura"},
    {"key": "fs", "name": "Fluid Structure", "label": "Organização Ágil"},
    {"key": "da", "name": "Digital Architecture", "label": "Tecnologia e Segurança"},
]

TA_DOMAIN_KEYS = tuple(key for key, _ in OPERATIONAL_DOMAINS)
LEACTION_F_DOMAINS: tuple[str, ...] = (
    "Estratégia",
    "Governança",
    "Pessoas",
    "Processos",
    "Dados",
    "Aplicações",
    "Infraestrutura",
    "Segurança",
    "Cultura",
)
LEACTION_F_TO_DOMAIN_KEY: dict[str, str] = {
    "Estratégia": "ds",
    "Governança": "dg",
    "Pessoas": "cc",
    "Processos": "bm",
    "Dados": "dc",
    "Aplicações": "dp",
    "Infraestrutura": "cap",
    "Segurança": "dm",
    "Cultura": "ic",
}
TA_TEMPORAL_KEYS = ("present", "future")
TA_PREFU_BY_TEMPORAL = {"present": "P", "future": "F"}
TA_TEMPORAL_LABELS = {"present": "Presente", "future": "Futuro"}
TA_QUESTIONS_PER_DIMENSION = len(OPERATIONAL_DOMAINS) * len(TA_TEMPORAL_KEYS)

APPROVAL_STATUS_UNDER_REVIEW = "under_review"
APPROVAL_STATUS_APPROVED = "approved"


def _format_operational_domains_spec() -> str:
    return "\n".join(
        f"  - {name} (domain_key: {key})"
        for key, name in OPERATIONAL_DOMAINS
    )


def _expansive_research_meta_framework_rules(
    sector_name: str,
    *,
    strategic_guidelines: str | None = None,
    operational_gemba: str | None = None,
    research_guidelines: str | None = None,
) -> str:
    strategic = (strategic_guidelines or research_guidelines or "").strip() or (
        "Não informados explicitamente — derive desafios estratégicos das referências web "
        "e benchmarks do setor."
    )
    gemba = (operational_gemba or "").strip() or (
        "Não especificado — proponha um módulo prático de execução no chão de fábrica "
        "adequado ao setor (ex.: diário de obra, checklist operacional, apontamento de horas)."
    )
    leaction_list = ", ".join(LEACTION_F_DOMAINS)
    domain_mapping = "\n".join(
        f'  - {name} → domain_key "{key}"'
        for name, key in LEACTION_F_TO_DOMAIN_KEY.items()
    )
    return f"""DIRETRIZ DE PESQUISA EXPANSIVA: O especialista forneceu os seguintes desafios estratégicos: {strategic}. E exigiu o seguinte foco de execução operacional (Gemba): {gemba}.
Você DEVE basear a sua estruturação nestas duas diretrizes e expandir a pesquisa para garantir uma cobertura holística do setor de {sector_name}.

REGRAS DO META-FRAMEWORK (Geração de Building Blocks):
Você DEVE criar no mínimo 9 "Blocos de Construção".
- Pelo menos um bloco para CADA UM dos 9 domínios do LeAction F ({leaction_list}).

REGRA CRÍTICA OPERACIONAL (GEMBA):
- VOCÊ DEVE criar um bloco ESPECÍFICO E EXCLUSIVO que represente a ferramenta/módulo prático operacional solicitado em "{gemba}" (ex: um aplicativo de Diário de Obra, módulo de checklist de frota, etc.). Este bloco deve ser classificado preferencialmente no domínio de "Aplicações" ou "Processos", com a camada TOGAF focada na operação real. Marque este bloco com "is_gemba_operational": true.

Anatomia de cada bloco (inclua TODOS os campos abaixo ALÉM dos campos PanelDX já exigidos):
1. title: Nome do bloco (também replique em block_name).
2. domain: O domínio exato LeAction F (um dos 9 listados acima).
3. domain_key: Chave canônica PanelDX correspondente ao domínio LeAction F:
{domain_mapping}
4. togaf_layer: Camada BDAT correspondente (Negócios, Dados, Aplicações, Tecnologia).
5. challenge_addressed: A dor resolvida.
6. architecture_building_block: Nome técnico canônico da solução (ex: "App Mobile de Coleta de Dados").
7. kpi: Métrica de sucesso prática no chão de fábrica.

Mínimo 9 blocos — exatamente um domain_key por chave canônica: {", ".join(TA_DOMAIN_KEYS)}."""


def _framework_definitions_prompt_block(action_name: str) -> str:
    definitions_code = get_framework_taxonomy_for_prompt()
    allowed_keys = ", ".join(TA_DOMAIN_KEYS)
    return f"""O documento abaixo é o descritivo completo do framework PanelDX:
- CANONICAL_FRAMEWORK_KNOWLEDGE: dimensões universais IMUTÁVEIS (SV, HC, FS, DA) — não gere nem altere.
- SECTOR_DIMENSION_TEMPLATE_LA: dimensão "{SECTOR_DIMENSION_TEMPLATE_KEY}" (Aprendizagem em Ação) — MODELO ESTRUTURAL
  que você SUBSTITUI integralmente pela 5ª dimensão setorial "{action_name}".
  Replique a granularidade de leaf_bloc e leaf_derv do template LA em cada domínio, com conteúdo do setor.

[INÍCIO DO DESCRITIVO CANÔNICO + TEMPLATE LA]
{definitions_code}
[FIM DO DESCRITIVO]

Regra de Ouro: Os blocos da nova dimensão '{action_name}' DEVEM usar os domain_key canônicos listados
(ex.: 'ds', 'bm', 'ic'…). Nunca invente siglas de domínio. Use exclusivamente: {allowed_keys}.
Alias legado aceito: dc_cap → cap."""


def _questionnaire_coverage_rules(
    *,
    sector_name: str,
    action_name: str,
    acronym: str,
) -> str:
    dimension_label = f"{action_name} - {acronym}"
    return f"""METODOLOGIA DE ELABORAÇÃO DO QUESTIONÁRIO (obrigatório):
1. LEITURA DA DOCUMENTAÇÃO PESQUISADA
   - Analise integralmente as REFERÊNCIAS WEB fornecidas antes de redigir qualquer pergunta.
   - Extraia dores operacionais, capacidades digitais, regulamentações, sistemas core e práticas
     típicas do setor {sector_name}.
   - Cada pergunta e cada rubrica devem refletir evidências dessa documentação — não invente
     conteúdo genérico desconectado das fontes.

2. COBERTURA MATRICIAL DA DIMENSÃO SETORIAL
   - Dimensão operacional: "{dimension_label}".
   - Domínios obrigatórios (9):
{_format_operational_domains_spec()}
   - Para CADA domínio, gere DUAS perguntas obrigatórias (padrão PanelDX prefu_ques):
     a) Presente (prefu_ques "P") — estado ATUAL da prática no setor.
     b) Futuro (prefu_ques "F") — perspectiva de EVOLUÇÃO/ADOÇÃO planejada.
   - Regra inviolável de cobertura: exatamente UMA pergunta por tripla (dimensão, domínio, temporalidade).
     Ou seja: 9 building_blocks × 2 temporalidades = {TA_QUESTIONS_PER_DIMENSION} perguntas no total.
   - Estrutura JSON: cada building_block contém "assessment_questions" com chaves "present" e "future".
   - Não agrupe domínios, não omita domain_key, não omita Presente ou Futuro em nenhum domínio.

3. RUBRICAS SETORIAIS (obrigatório em cada pergunta)
   - Inclua o array "options" com EXATAMENTE 6 itens (grad 0 a 5) em TODA pergunta (Presente e Futuro).
   - Cada option deve ter:
     * "grad": inteiro 0-5
     * "label_rubr": rótulo CURTO (2 a 5 palavras, máx. ~30 caracteres), específico ao setor e ao domínio
     * "desc_rubr": frase COMPLETA (1-2 frases) contextualizada ao setor {sector_name}, domínio e temporalidade
   - Presente (prefu_ques "P"): descreva o ESTADO ATUAL da prática no setor (maturidade operacional).
   - Futuro (prefu_ques "F"): descreva o HORIZONTE DE ADOÇÃO/EVOLUÇÃO no setor (não repita as rubricas de Presente).
   - PROIBIDO: rubricas genéricas copiadas de escalas universais, textos truncados, labels iguais à descrição inteira,
     ou desc_rubr com reticências/corte no meio da frase.
   - As rubricas devem ser tão específicas quanto as perguntas — fundamentadas na documentação pesquisada.
   - O bloco de exemplo no JSON abaixo é apenas ESTRUTURAL: personalize label_rubr e desc_rubr em cada domínio;
     não copie literalmente os textos ilustrativos do exemplo.

4. QUALIDADE DAS PERGUNTAS
   - Presente: question_text sobre "como está hoje" no domínio.
   - Futuro: question_text sobre "qual a perspectiva/planejamento de evolução" no domínio.
   - O block_name e block_description devem amarrar o par de perguntas ao domínio e à documentação lida.

5. ESTRUTURA METODOLÓGICA (leaf_bloc / leaf_derv — substitui LA)
   - Consulte SECTOR_DIMENSION_TEMPLATE_LA no descritivo canônico: é o modelo de blocos e entregáveis por domínio.
   - Em cada building_block inclua "leaf_blocks": lista de blocos metodológicos do domínio (como no template LA),
     cada um com "name_bloc", "desc_bloc" e "deliverables" [{{"name_derv", "desc_derv", "derv_comp"}}].
   - Adapte nomes, composições e KPIs ao setor {sector_name}; não copie literalmente os textos do template LA."""


def _sector_rubric_options_example(*, temporal: str) -> str:
    if temporal == "future":
        return """            "options": [
              {"grad": 0, "label_rubr": "Sem previsão", "desc_rubr": "Não há plano ou orçamento para evoluir esta capacidade no setor nos próximos anos."},
              {"grad": 1, "label_rubr": "Longo prazo", "desc_rubr": "Evolução prevista apenas para horizonte de longo prazo, sem iniciativas estruturadas no curto/médio prazo."},
              {"grad": 2, "label_rubr": "Médio prazo (P)", "desc_rubr": "Adoção parcialmente prevista no médio prazo, ainda sem compromisso formal de investimento."},
              {"grad": 3, "label_rubr": "Médio prazo (E)", "desc_rubr": "Adoção totalmente prevista e orçada para o médio prazo no contexto setorial."},
              {"grad": 4, "label_rubr": "Curto prazo (P)", "desc_rubr": "Implementação parcial já iniciada com conclusão prevista no curto prazo."},
              {"grad": 5, "label_rubr": "Curto prazo (T)", "desc_rubr": "Prioridade imediata de adoção/evolução (próximos 90 dias) no setor."}
            ]"""
    return """            "options": [
              {"grad": 0, "label_rubr": "Inexistente", "desc_rubr": "Não há prática formalizada desta capacidade no contexto do setor e do domínio avaliado."},
              {"grad": 1, "label_rubr": "Incipiente", "desc_rubr": "Prática incipiente, sem processos estruturados nem governança formal no setor."},
              {"grad": 2, "label_rubr": "Experimental", "desc_rubr": "Prática em experimentação ou estruturação inicial, com pilotos pontuais no setor."},
              {"grad": 3, "label_rubr": "Estabelecido", "desc_rubr": "Prática documentada, estabelecida e comunicada oficialmente na operação setorial."},
              {"grad": 4, "label_rubr": "Consolidado", "desc_rubr": "Prática consolidada, monitorada e integrada à operação do setor."},
              {"grad": 5, "label_rubr": "Otimizado", "desc_rubr": "Prática otimizada e revisada dinamicamente com base em dados e melhoria contínua no setor."}
            ]"""


def _sector_building_block_json_example(sector_name: str) -> str:
    present_opts = _sector_rubric_options_example(temporal="present")
    future_opts = _sector_rubric_options_example(temporal="future")
    return f"""      {{
        "title": "Nome do bloco (meta-framework LeAction F)",
        "domain": "Estratégia",
        "domain_key": "ds",
        "domain_name": "Digital Strategy",
        "togaf_layer": "Negócios",
        "challenge_addressed": "Dor setorial que este bloco resolve",
        "architecture_building_block": "Nome técnico canônico da solução",
        "kpi": "Métrica de sucesso mensurável",
        "is_gemba_operational": false,
        "block_name": "Nome do bloco (resumo do domínio no setor)",
        "block_description": "Descrição do domínio no contexto de {sector_name}",
        "leaf_blocks": [
          {{
            "name_bloc": "Processo setorial (leaf_bloc)",
            "desc_bloc": "Descrição do processo adaptado ao setor",
            "deliverables": [
              {{
                "name_derv": "Entregável / KPI (leaf_derv)",
                "desc_derv": "Definição completa do entregável no contexto de {sector_name}",
                "derv_comp": "Composição: itens que formam o entregável"
              }}
            ]
          }}
        ],
        "assessment_questions": {{
          "present": {{
            "prefu_ques": "P",
            "question_text": "Como está hoje a prática de Estratégia Digital no contexto de {sector_name}?",
            "question_type": "multiple_choice",
{present_opts}
          }},
          "future": {{
            "prefu_ques": "F",
            "question_text": "Qual a perspectiva de evolução da Estratégia Digital em {sector_name}?",
            "question_type": "multiple_choice",
{future_opts}
          }}
        }}
      }}"""


def _repair_ai_json_text(text: str) -> str:
    repaired = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired.strip()


def _close_truncated_json(text: str) -> str:
    """Fecha aspas/chaves abertas em JSON possivelmente truncado pela IA."""
    stack: list[str] = []
    in_string = False
    escape = False

    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]" and stack and stack[-1] == ch:
            stack.pop()

    suffix = ""
    if in_string:
        suffix += '"'
    suffix += "".join(reversed(stack))
    return text + suffix


UNIVERSAL_AXIS_PREFIXES = ("SV —", "HC —", "FS —", "DA —")

SECTOR_ACTION_META: dict[str, tuple[str, str]] = {
    "telecom": ("TA", "Telecom Action"),
    "telecomunicações": ("TA", "Telecom Action"),
    "telecomunicacoes": ("TA", "Telecom Action"),
    "telco": ("TA", "Telecom Action"),
    "varejo": ("RA", "Retail Action"),
    "retail": ("RA", "Retail Action"),
    "saúde": ("HA", "Health Action"),
    "saude": ("HA", "Health Action"),
    "health": ("HA", "Health Action"),
    "healthcare": ("HA", "Health Action"),
    "indústria": ("IA", "Industry Action"),
    "industria": ("IA", "Industry Action"),
    "manufatura": ("MA", "Manufacturing Action"),
    "educação": ("LA", "Aprendizagem em Ação"),
    "educacao": ("LA", "Aprendizagem em Ação"),
    "education": ("LA", "Aprendizagem em Ação"),
    "financeiro": ("FA", "Financial Action"),
    "finance": ("FA", "Financial Action"),
    "bancos": ("FA", "Financial Action"),
}

# 18 perguntas TA (9 domínios × Presente/Futuro) exigem resposta JSON extensa.
SECTOR_AI_MAX_TOKENS = 16_384

REQUIRED_ROOT_KEYS = (
    "sources",
    "manifest",
    "maturity_levels",
    "operational_dimension",
)


class FrameworkBuilderService:
    def build_framework_for_sector(
        self,
        sector_name: str,
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> dict[str, Any]:
        """Pipeline completo: persiste framework no banco (IA apenas para setores sob demanda)."""
        sector = normalize_sector_name(sector_name)
        if not sector:
            raise ValueError("O nome do setor é obrigatório.")

        if is_canonical_education_sector(sector):
            framework_id = ensure_education_framework()
            count = AssessmentItem.query.filter_by(framework_id=framework_id).count()
            return {
                "status": "exists",
                "message": (
                    "O framework Educação (educacao-v1) é o catálogo base da aplicação "
                    "e já está persistido — não requer pesquisa nem IA."
                ),
                "framework_id": framework_id,
                "sector": sector,
                "assessment_items_count": count,
            }

        framework_id = self._framework_id_for_sector(sector)
        acronym, action_name = self._sector_action_meta(sector)

        existing = db.session.get(Framework, framework_id)
        if existing:
            universal_count = AssessmentItem.query.filter_by(framework_id=framework_id).count()
            return {
                "status": "exists",
                "message": f"Framework '{framework_id}' já existe.",
                "framework_id": framework_id,
                "sector": sector,
                "assessment_items_count": universal_count,
            }

        # PASSO 1 — Framework base + níveis de maturidade
        framework = Framework(
            id=framework_id,
            name=f"Chamelleon — {sector.title()}",
            industry=sector,
            version="1.0",
            rules_metadata={
                "sector": sector,
                "operational_dimension_acronym": acronym,
                "operational_dimension_name": f"{action_name} - {acronym}",
                "universal_dimensions": universal_dimensions_summary(),
                "scale_min": 1,
                "scale_max": 4,
            },
            is_active=True,
        )
        db.session.add(framework)

        for level, name, description in DEFAULT_MATURITY_LEVELS:
            db.session.add(
                MaturityLevel(
                    framework_id=framework_id,
                    level=level,
                    name=name,
                    description=description,
                )
            )

        # PASSO 2 — Importar catálogo universal (4 dimensões fixas)
        universal_items = load_universal_assessment_items(for_new_framework=True)
        universal_inserted = 0
        for item_data in universal_items:
            meta = dict(item_data.get("metadata") or {})
            meta["dimension_type"] = "universal"
            db.session.add(
                AssessmentItem(
                    framework_id=framework_id,
                    axis=item_data["axis"],
                    question_text=item_data["question_text"],
                    question_type=item_data["question_type"],
                    options=normalize_rubric_options(item_data.get("options") or []),
                    item_metadata=meta,
                )
            )
            universal_inserted += 1

        # PASSO 3 — Pesquisa web + 5ª dimensão setorial via Claude
        search_results = search_sector_references(sector)
        sector_payload = self._generate_sector_dimension(
            sector,
            acronym,
            action_name,
            search_results,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )
        sector_inserted = self._persist_sector_assessment_items(
            framework_id,
            sector_payload,
            acronym,
            action_name,
            sector_slug=sector,
        )

        framework.rules_metadata = {
            **(framework.rules_metadata or {}),
            "operational_dimension": sector_payload.get("operational_dimension", {}),
            "research_sources": sector_payload.get("sources", []),
        }

        db.session.commit()

        return {
            "status": "created",
            "framework_id": framework_id,
            "sector": sector,
            "operational_dimension": f"{action_name} - {acronym}",
            "universal_items_inserted": universal_inserted,
            "sector_items_inserted": sector_inserted,
            "total_assessment_items": universal_inserted + sector_inserted,
            "maturity_levels": len(DEFAULT_MATURITY_LEVELS),
        }

    def research_and_propose(
        self,
        sector_name: str,
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> dict[str, Any]:
        """Preview editável — Educação vem do banco; demais setores usam pesquisa + IA."""
        sector = normalize_sector_name(sector_name)
        if not sector:
            raise ValueError("O nome do setor é obrigatório.")

        if is_canonical_education_sector(sector):
            ensure_education_framework()
            proposal = self.get_framework_detail(DEV_FRAMEWORK_ID)
            proposal["sources"] = []
            proposal["research_snippets"] = []
            proposal["universal_assessment_preview"] = load_universal_assessment_items(
                for_new_framework=True
            )
            proposal["assessment_items"] = self._flatten_assessment_items(
                proposal.get("operational_dimension") or {}
            )
            return proposal

        search_results = search_sector_references(sector)
        if not search_results:
            raise RuntimeError(
                f"Nenhuma referência encontrada na web para o setor '{sector}'."
            )

        acronym, action_name = self._sector_action_meta(sector)
        sector_payload = self._generate_sector_dimension(
            sector,
            acronym,
            action_name,
            search_results,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )
        proposal = self._assemble_framework_proposal(sector, sector_payload)
        self._validate_proposal(proposal)

        proposal["sector"] = sector
        proposal["framework_id_preview"] = self._framework_id_for_sector(sector)
        proposal["research_snippets"] = search_results
        proposal["universal_dimensions"] = UNIVERSAL_DIMENSIONS
        proposal["methodology_structure"] = build_full_methodology_document(
            operational_dimension=proposal.get("operational_dimension"),
        )
        proposal["universal_assessment_preview"] = load_universal_assessment_items(
            for_new_framework=True
        )
        proposal["assessment_items"] = self._flatten_assessment_items(
            proposal["operational_dimension"]
        )

        framework_id = self._framework_id_for_sector(sector)
        existing = db.session.get(Framework, framework_id)
        if existing:
            existing_status = (existing.rules_metadata or {}).get(
                "approval_status", APPROVAL_STATUS_APPROVED
            )
            if existing_status == APPROVAL_STATUS_APPROVED:
                raise ValueError(
                    f"Já existe um framework aprovado para '{sector}' ({framework_id}). "
                    "Abra pelo catálogo para editar ou remova antes de gerar um novo."
                )

        persist_result = self.persist_under_review(proposal)
        proposal["approval_status"] = APPROVAL_STATUS_UNDER_REVIEW
        proposal["is_published"] = True
        proposal["framework_id_preview"] = persist_result["framework_id"]
        proposal["persist_status"] = persist_result.get("status")
        return proposal

    def list_frameworks(self) -> list[dict[str, Any]]:
        """Lista frameworks publicados no catálogo."""
        frameworks = Framework.query.order_by(Framework.name.asc()).all()
        catalog: list[dict[str, Any]] = []

        for framework in frameworks:
            metadata = framework.rules_metadata or {}
            op_dim = metadata.get("operational_dimension") or {}
            catalog.append(
                {
                    "id": framework.id,
                    "name": framework.name,
                    "sector": metadata.get("sector") or framework.industry,
                    "industry": framework.industry,
                    "version": framework.version,
                    "is_active": framework.is_active,
                    "approval_status": metadata.get(
                        "approval_status", APPROVAL_STATUS_APPROVED
                    ),
                    "operational_dimension": metadata.get("operational_dimension_name")
                    or op_dim.get("full_label"),
                    "assessment_items_count": AssessmentItem.query.filter_by(
                        framework_id=framework.id
                    ).count(),
                    "maturity_levels_count": MaturityLevel.query.filter_by(
                        framework_id=framework.id
                    ).count(),
                    "is_canonical": is_canonical_education_framework(framework.id),
                    "is_default": framework.id == DEV_FRAMEWORK_ID,
                }
            )

        catalog.sort(key=lambda row: (0 if row.get("is_default") else 1, row.get("name") or ""))
        return catalog

    def get_framework_detail(self, framework_id: str) -> dict[str, Any]:
        """Carrega framework publicado do banco — sem pesquisa web nem IA."""
        framework = db.session.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework '{framework_id}' não encontrado.")

        metadata = framework.rules_metadata or {}
        is_canonical = (
            is_canonical_education_framework(framework_id)
            or metadata.get("is_canonical_la")
            or metadata.get("ingestion_complete")
        )

        levels = (
            MaturityLevel.query.filter_by(framework_id=framework_id)
            .order_by(MaturityLevel.level.asc())
            .all()
        )
        all_items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
        universal_items = [item for item in all_items if self._is_universal_axis(item.axis)]
        sector_items = [item for item in all_items if not self._is_universal_axis(item.axis)]

        op_dim = copy.deepcopy(metadata.get("operational_dimension") or {})
        if op_dim.get("building_blocks") and sector_items:
            self._overlay_sector_questions_on_blocks(op_dim, sector_items)
        elif sector_items:
            blocks = self._sector_items_to_building_blocks(sector_items)
            blocks = self._sort_blocks_by_domain(blocks)
            op_dim = self._build_operational_dimension_from_blocks(blocks, metadata, framework)
        elif not op_dim.get("building_blocks"):
            op_dim = self._build_operational_dimension_from_blocks([], metadata, framework)

        manifest = metadata.get("manifest") or {
            "name": framework.name,
            "descricao": "",
        }

        methodology = metadata.get("methodology_document")
        if not methodology:
            methodology = build_full_methodology_document(
                operational_dimension=op_dim,
            )

        taxonomy = None
        try:
            ensure_framework_taxonomy(framework_id)
            taxonomy = get_framework_taxonomy(framework_id)
        except Exception as exc:
            logger.warning("Taxonomia indisponível para '%s': %s", framework_id, exc)

        return {
            "sector": metadata.get("sector") or framework.industry or "",
            "framework_id_preview": framework.id,
            "approval_status": metadata.get(
                "approval_status", APPROVAL_STATUS_APPROVED
            ),
            "is_published": True,
            "is_canonical": is_canonical,
            "is_read_only": is_canonical_education_framework(framework_id),
            "manifest": manifest,
            "maturity_levels": [
                {
                    "level": level.level,
                    "name": level.name,
                    "description": level.description,
                }
                for level in levels
            ],
            "operational_dimension": op_dim,
            "universal_dimensions": metadata.get("universal_dimensions") or UNIVERSAL_DIMENSIONS,
            "sources": metadata.get("research_sources") or metadata.get("sources") or [],
            "methodology_counts": metadata.get("methodology_counts"),
            "universal_assessment_count": len(universal_items),
            "sector_assessment_count": len(sector_items),
            "methodology_structure": methodology,
            "taxonomy": taxonomy,
        }

    @classmethod
    def _overlay_sector_questions_on_blocks(
        cls,
        op_dim: dict[str, Any],
        sector_items: list[AssessmentItem],
    ) -> None:
        """Atualiza perguntas/rubricas nos building_blocks preservando leaf_blocks."""
        by_domain: dict[str, dict[str, dict[str, Any]]] = {}
        for item in sector_items:
            domain_key = cls._domain_key_for_item(item)
            if not domain_key:
                continue
            prefu = cls._prefu_for_item(item)
            temporal_key = "future" if prefu == "F" else "present"
            by_domain.setdefault(domain_key, {})[temporal_key] = {
                "prefu_ques": prefu,
                "question_text": item.question_text,
                "question_type": item.question_type,
                "options": item.options or [],
            }

        for block in op_dim.get("building_blocks") or []:
            domain_key = block.get("domain_key")
            if not domain_key:
                continue
            qmap = by_domain.get(domain_key)
            if not qmap:
                continue
            existing = block.get("assessment_questions") or {}
            block["assessment_questions"] = {**existing, **qmap}

    def get_persisted_methodology(self, framework_id: str) -> dict[str, Any]:
        """Recupera metodologia leaf_bloc/leaf_derv já persistida."""
        framework = db.session.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework '{framework_id}' não encontrado.")

        metadata = framework.rules_metadata or {}
        stored = metadata.get("methodology_document")
        if stored:
            return stored

        op_dim = metadata.get("operational_dimension") or {}
        return build_full_methodology_document(operational_dimension=op_dim)

    def update_framework(self, framework_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
        """Atualiza framework publicado com dados revisados."""
        framework = db.session.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework '{framework_id}' não encontrado.")

        sector_raw = proposal.get("sector") or framework.industry or ""
        sector = normalize_sector_name(str(sector_raw))
        if not sector:
            raise ValueError("Setor ausente na proposta.")

        self._validate_proposal(
            {
                "sources": proposal.get("sources", []),
                "manifest": proposal.get("manifest", {}),
                "maturity_levels": proposal.get("maturity_levels", []),
                "operational_dimension": proposal.get("operational_dimension", {}),
            }
        )

        manifest = proposal["manifest"]
        op_dim = proposal["operational_dimension"]
        acronym = (op_dim.get("acronym") or self._sector_action_meta(sector)[0]).upper()
        action_name = op_dim.get("name") or self._sector_action_meta(sector)[1]
        full_label = op_dim.get("full_label") or f"{action_name} - {acronym}"

        existing_meta = framework.rules_metadata or {}
        approval_status = existing_meta.get("approval_status", APPROVAL_STATUS_APPROVED)

        framework.name = manifest.get("name") or framework.name
        framework.industry = sector
        framework.is_active = approval_status == APPROVAL_STATUS_APPROVED
        framework.rules_metadata = self._build_rules_metadata(
            proposal, sector, acronym, full_label, op_dim, approval_status=approval_status
        )

        MaturityLevel.query.filter_by(framework_id=framework_id).delete()
        for level_data in proposal.get("maturity_levels", []):
            db.session.add(
                MaturityLevel(
                    framework_id=framework_id,
                    level=int(level_data["level"]),
                    name=str(level_data.get("name", "")),
                    description=level_data.get("description"),
                )
            )

        sector_inserted = self._persist_sector_assessment_items(
            framework_id,
            {"operational_dimension": op_dim},
            acronym,
            action_name,
            sector_slug=sector,
        )

        db.session.commit()

        self._import_framework_taxonomy(framework_id, framework.rules_metadata)

        return {
            "status": "updated",
            "framework_id": framework_id,
            "name": framework.name,
            "sector": sector,
            "operational_dimension": full_label,
            "sector_items_inserted": sector_inserted,
            "message": f"Framework '{framework_id}' atualizado com sucesso.",
        }

    def delete_framework(self, framework_id: str) -> dict[str, Any]:
        """Remove um framework do catálogo (exceto o framework base Educação)."""
        if is_canonical_education_framework(framework_id):
            raise ValueError(
                "O framework Educação (educacao-v1) é o catálogo base e não pode ser removido."
            )

        framework = db.session.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework '{framework_id}' não encontrado.")

        name = framework.name
        db.session.delete(framework)
        db.session.commit()

        return {
            "status": "deleted",
            "framework_id": framework_id,
            "name": name,
            "message": f"Framework '{framework_id}' removido do catálogo.",
        }

    def persist_under_review(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Salva proposta gerada pela IA com status em análise (visível no catálogo admin)."""
        return self._persist_proposal(
            proposal,
            approval_status=APPROVAL_STATUS_UNDER_REVIEW,
            replace_existing=True,
            relink_tenants=False,
        )

    def publish_proposal(
        self, proposal: dict[str, Any], *, replace_existing: bool = False
    ) -> dict[str, Any]:
        """Aprova framework — torna-o ativo e disponível para cadastro de leads."""
        return self._persist_proposal(
            proposal,
            approval_status=APPROVAL_STATUS_APPROVED,
            replace_existing=replace_existing,
            relink_tenants=True,
        )

    def _persist_proposal(
        self,
        proposal: dict[str, Any],
        *,
        approval_status: str = APPROVAL_STATUS_APPROVED,
        replace_existing: bool = False,
        relink_tenants: bool = False,
    ) -> dict[str, Any]:
        """Persiste proposta no banco com status de aprovação configurável."""
        sector_raw = proposal.get("sector", "")
        sector = normalize_sector_name(str(sector_raw))
        if not sector:
            raise ValueError("Setor ausente na proposta.")

        self._validate_proposal(
            {
                "sources": proposal.get("sources", []),
                "manifest": proposal.get("manifest", {}),
                "maturity_levels": proposal.get("maturity_levels", []),
                "operational_dimension": proposal.get("operational_dimension", {}),
            }
        )

        framework_id = proposal.get("framework_id_preview") or self._framework_id_for_sector(
            sector
        )
        existing = db.session.get(Framework, framework_id)
        is_approved = approval_status == APPROVAL_STATUS_APPROVED

        if existing:
            existing_status = (existing.rules_metadata or {}).get(
                "approval_status", APPROVAL_STATUS_APPROVED
            )
            if (
                existing_status == APPROVAL_STATUS_APPROVED
                and is_approved
                and not replace_existing
            ):
                return {
                    "status": "exists",
                    "message": (
                        f"O framework '{framework_id}' já está aprovado. "
                        "Você pode substituir a versão existente ou removê-lo do catálogo."
                    ),
                    "framework_id": framework_id,
                    "name": existing.name,
                    "approval_status": existing_status,
                    "can_replace": True,
                }
            if existing_status == APPROVAL_STATUS_APPROVED and not is_approved:
                raise ValueError(
                    f"O framework '{framework_id}' já está aprovado e não pode voltar para análise."
                )
            if existing_status == APPROVAL_STATUS_UNDER_REVIEW:
                replace_existing = True

        if existing and replace_existing:
            db.session.delete(existing)
            db.session.flush()

        manifest = proposal["manifest"]
        op_dim = proposal["operational_dimension"]
        acronym = (op_dim.get("acronym") or self._sector_action_meta(sector)[0]).upper()
        action_name = op_dim.get("name") or self._sector_action_meta(sector)[1]
        full_label = op_dim.get("full_label") or f"{action_name} - {acronym}"

        framework = Framework(
            id=framework_id,
            name=manifest.get("name") or f"Chamelleon — {sector.title()}",
            industry=sector,
            version="1.0",
            rules_metadata=self._build_rules_metadata(
                proposal, sector, acronym, full_label, op_dim, approval_status=approval_status
            ),
            is_active=is_approved,
        )
        db.session.add(framework)

        for level_data in proposal.get("maturity_levels", []):
            db.session.add(
                MaturityLevel(
                    framework_id=framework_id,
                    level=int(level_data["level"]),
                    name=str(level_data.get("name", "")),
                    description=level_data.get("description"),
                )
            )

        universal_items = load_universal_assessment_items(for_new_framework=True)
        for item_data in universal_items:
            meta = dict(item_data.get("metadata") or {})
            meta["dimension_type"] = "universal"
            db.session.add(
                AssessmentItem(
                    framework_id=framework_id,
                    axis=item_data["axis"],
                    question_text=item_data["question_text"],
                    question_type=item_data["question_type"],
                    options=normalize_rubric_options(item_data.get("options") or []),
                    item_metadata=meta,
                )
            )

        sector_inserted = self._persist_sector_assessment_items(
            framework_id,
            {"operational_dimension": op_dim},
            acronym,
            action_name,
            sector_slug=sector,
        )

        db.session.commit()

        self._import_framework_taxonomy(framework_id, framework.rules_metadata)

        relinked = 0
        if relink_tenants and is_approved:
            relinked = relink_orphan_lead_tenants(framework_id, sector)

        if not is_approved:
            result_status = "under_review"
            message = (
                f"Framework '{framework_id}' salvo com status em análise. "
                "Revise no catálogo e aprove quando estiver pronto."
            )
        else:
            result_status = "replaced" if replace_existing and existing else "approved"
            message = (
                f"Framework '{framework_id}' substituído e aprovado com sucesso."
                if result_status == "replaced"
                else f"Framework '{framework_id}' aprovado e disponível para uso."
            )

        return {
            "status": result_status,
            "framework_id": framework_id,
            "sector": sector,
            "name": framework.name,
            "approval_status": approval_status,
            "operational_dimension": full_label,
            "universal_items_inserted": len(universal_items),
            "sector_items_inserted": sector_inserted,
            "total_assessment_items": len(universal_items) + sector_inserted,
            "tenants_relinked": relinked,
            "message": message,
        }

    @staticmethod
    def _import_framework_taxonomy(
        framework_id: str,
        rules_metadata: dict[str, Any] | None,
    ) -> None:
        """Persiste leaf_dime/doma/bloc/derv após publicação ou atualização."""
        try:
            if is_canonical_education_framework(framework_id):
                import_taxonomy_from_legacy(framework_id)
            else:
                import_taxonomy_from_methodology_document(
                    framework_id,
                    (rules_metadata or {}).get("methodology_document"),
                )
        except Exception as exc:
            logger.warning(
                "Falha ao importar taxonomia para '%s': %s",
                framework_id,
                exc,
            )

    @classmethod
    def _default_maturity_levels_payload(cls) -> list[dict[str, Any]]:
        return [
            {"level": level, "name": name, "description": desc}
            for level, name, desc in DEFAULT_MATURITY_LEVELS
        ]

    def _assemble_framework_proposal(
        self,
        sector: str,
        sector_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Monta proposta completa a partir da 5ª dimensão gerada pela IA."""
        return {
            "sources": sector_payload.get("sources") or [],
            "manifest": {
                "name": f"Chamelleon — Framework {sector.title()}",
                "descricao": (
                    f"Framework de diagnóstico de maturidade digital para o setor "
                    f"{sector}, com dimensões universais PanelDX e core operacional setorial."
                ),
            },
            "maturity_levels": self._default_maturity_levels_payload(),
            "operational_dimension": sector_payload["operational_dimension"],
        }

    def _generate_sector_dimension(
        self,
        sector: str,
        acronym: str,
        action_name: str,
        search_results: list[dict[str, str]],
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> dict[str, Any]:
        prompt = self.build_framework_from_doc(
            sector,
            acronym,
            action_name,
            search_results,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )
        raw_response = invoke_claude(prompt, max_tokens=SECTOR_AI_MAX_TOKENS)
        payload = self._parse_ai_json(raw_response)
        self._normalize_meta_building_blocks(payload)
        self._hydrate_sector_rubrics(payload)
        self._validate_sector_payload(payload, acronym)
        return payload

    def build_framework_from_doc(
        self,
        sector_name: str,
        acronym: str,
        action_name: str,
        search_results: list[dict[str, str]],
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> str:
        """Monta o prompt Claude com definições canônicas PanelDX para a 5ª dimensão setorial."""
        references = "\n\n".join(
            f"- Título: {item['title']}\n  URL: {item['url']}\n  Trecho: {item['snippet']}"
            for item in search_results
        )
        coverage_rules = _questionnaire_coverage_rules(
            sector_name=sector_name,
            action_name=action_name,
            acronym=acronym,
        )
        block_example = _sector_building_block_json_example(sector_name)
        definitions_block = _framework_definitions_prompt_block(action_name)
        expansive_rules = _expansive_research_meta_framework_rules(
            sector_name,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )

        return f"""Você é um Arquiteto Especialista em Transformação Digital e Agente responsável
pela elaboração do questionário diagnóstico setorial do framework Chamelleon.

O framework já possui 4 dimensões universais IMUTÁVEIS (Shared Vision, Heart Connection,
Fluid Structure, Digital Architecture) importadas do catálogo canônico PanelDX.

Sua missão é gerar EXCLUSIVAMENTE a 5ª Dimensão Operacional para o setor: {sector_name}.
Nomeie-a como "{action_name} - {acronym}".

Esta geração ocorre UMA ÚNICA VEZ no setup do setor pelo administrador — seja expansivo e holístico.

{expansive_rules}

{definitions_block}

{coverage_rules}

Use as referências web pesquisadas para fundamentar cada pergunta e rubrica.

REFERÊNCIAS WEB COLETADAS:
{references}

RETORNE APENAS JSON VÁLIDO (sem markdown) nesta estrutura.
IMPORTANTE: cada pergunta (present e future) DEVE incluir "options" com 6 rubricas setoriais (grad 0-5).

{{
  "sources": ["url1", "url2"],
  "operational_dimension": {{
    "name": "{action_name}",
    "acronym": "{acronym}",
    "full_label": "{action_name} - {acronym}",
    "description": "Visão da dimensão operacional do setor {sector_name}",
    "building_blocks": [
{block_example}
    ]
  }}
}}

REGRAS DE VALIDAÇÃO (o JSON será rejeitado se violar):
1. building_blocks: exatamente 9 itens — um por domain_key: {", ".join(TA_DOMAIN_KEYS)}.
2. Cobertura: em cada building_block, "assessment_questions.present" E "assessment_questions.future".
   Total: {TA_QUESTIONS_PER_DIMENSION} perguntas ({len(TA_DOMAIN_KEYS)} domínios × 2 temporalidades).
3. Cada pergunta: question_type "multiple_choice", prefu_ques ("P" ou "F") e "options" com 6 rubricas (grad 0-5, label_rubr + desc_rubr).
4. Conteúdo específico ao setor {sector_name}, fundamentado nas referências web.
5. NÃO inclua as 4 dimensões universais — apenas a 5ª dimensão setorial.
"""

    def _build_sector_only_prompt(
        self,
        sector_name: str,
        acronym: str,
        action_name: str,
        search_results: list[dict[str, str]],
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> str:
        return self.build_framework_from_doc(
            sector_name,
            acronym,
            action_name,
            search_results,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )

    def _build_proposal_prompt(
        self,
        sector_name: str,
        acronym: str,
        action_name: str,
        search_results: list[dict[str, str]],
        *,
        strategic_guidelines: str | None = None,
        operational_gemba: str | None = None,
        research_guidelines: str | None = None,
    ) -> str:
        references = "\n\n".join(
            f"- Título: {item['title']}\n  URL: {item['url']}\n  Trecho: {item['snippet']}"
            for item in search_results
        )
        domains_spec = _format_operational_domains_spec()
        coverage_rules = _questionnaire_coverage_rules(
            sector_name=sector_name,
            action_name=action_name,
            acronym=acronym,
        )
        block_example = _sector_building_block_json_example(sector_name)
        definitions_block = _framework_definitions_prompt_block(action_name)
        expansive_rules = _expansive_research_meta_framework_rules(
            sector_name,
            strategic_guidelines=strategic_guidelines,
            operational_gemba=operational_gemba,
            research_guidelines=research_guidelines,
        )

        return f"""Você é um Arquiteto Especialista em Transformação Digital e Agente responsável
pela elaboração do questionário diagnóstico setorial do framework Chamelleon.

Sua missão é expandir o framework metodológico para o setor: {sector_name}.

Esta geração ocorre UMA ÚNICA VEZ no setup do setor pelo administrador — seja expansivo e holístico.

{expansive_rules}

O framework base possui uma matriz estruturada por Dimensões (linhas) e Domínios (colunas).
Quatro dimensões são universais e IMUTÁVEIS (não as recrie, apenas referencie no manifest):
1. Shared Vision (Estratégia)
2. Heart Connection (Humano e Cultura)
3. Fluid Structure (Organização Ágil)
4. Digital Architecture (Tecnologia e Segurança)

Gere EXCLUSIVAMENTE a 5ª Dimensão Operacional — o "Core Operacional" do setor.
Nomeie-a: "{action_name} - {acronym}".

{definitions_block}

{coverage_rules}

Use os snippets de pesquisa web abaixo como documentação de referência obrigatória.

Domínios da dimensão setorial (9 building blocks obrigatórios):
{domains_spec}

REFERÊNCIAS WEB COLETADAS:
{references}

RETORNE APENAS UM JSON VÁLIDO (sem markdown, sem texto extra) com esta estrutura:

{{
  "sources": ["url1", "url2"],
  "manifest": {{
    "name": "Chamelleon — Framework {sector_name}",
    "descricao": "Descrição executiva do framework setorial"
  }},
  "maturity_levels": [
    {{ "level": 1, "name": "Reativo", "description": "..." }},
    {{ "level": 2, "name": "Gerenciado", "description": "..." }},
    {{ "level": 3, "name": "Integrado", "description": "..." }},
    {{ "level": 4, "name": "Preditivo", "description": "..." }}
  ],
  "operational_dimension": {{
    "name": "{action_name}",
    "acronym": "{acronym}",
    "full_label": "{action_name} - {acronym}",
    "description": "Visão da dimensão operacional do setor",
    "building_blocks": [
{block_example}
    ]
  }}
}}

REGRAS DE VALIDAÇÃO (o JSON será rejeitado se violar):
1. building_blocks: exatamente 9 itens — um por domain_key: {", ".join(TA_DOMAIN_KEYS)}.
2. Cobertura: em cada building_block, "assessment_questions.present" E "assessment_questions.future".
   Total: {TA_QUESTIONS_PER_DIMENSION} perguntas ({len(TA_DOMAIN_KEYS)} domínios × 2 temporalidades).
3. Cada pergunta: question_type "multiple_choice", prefu_ques ("P" ou "F") e "options" com 6 rubricas setoriais (grad 0-5).
4. maturity_levels: exatamente 4 níveis (1 a 4), nomes: Reativo, Gerenciado, Integrado, Preditivo.
5. sources: URLs mais relevantes das referências fornecidas.
6. Conteúdo específico ao setor {sector_name}, fundamentado na documentação pesquisada.
"""

    def _persist_sector_assessment_items(
        self,
        framework_id: str,
        sector_payload: dict[str, Any],
        acronym: str,
        action_name: str,
        *,
        sector_slug: str | None = None,
    ) -> int:
        """Grava questões setoriais (TA) — 2 por domínio (Presente + Futuro), preserva IDs."""
        op_dim = sector_payload["operational_dimension"]
        full_label = op_dim.get("full_label") or f"{action_name} - {acronym}"
        saved = 0

        existing_by_domain_prefu: dict[tuple[str, str], AssessmentItem] = {}
        for item in AssessmentItem.query.filter_by(framework_id=framework_id).all():
            if self._is_universal_axis(item.axis):
                continue
            domain_key = self._domain_key_for_item(item)
            if not domain_key:
                continue
            prefu = self._prefu_for_item(item)
            existing_by_domain_prefu[(domain_key, prefu)] = item

        for block in op_dim.get("building_blocks", []):
            domain_key = block.get("domain_key", "")
            if not domain_key:
                continue
            domain_name = block.get("domain_name", domain_key)
            base_metadata = {
                "domain_key": domain_key,
                "domain_name": domain_name,
                "dimension_type": "sector",
                "sector": sector_slug,
                "block_name": block.get("block_name"),
                "block_description": block.get("block_description"),
                "operational_acronym": acronym,
            }

            for temporal_key, prefu, question in self._iter_block_questions(block):
                temporal_label = TA_TEMPORAL_LABELS[temporal_key]
                axis = (
                    f"{acronym} — {full_label} / {domain_key} — {domain_name} ({temporal_label})"
                )
                options = self._normalize_options(
                    question.get("options", []),
                    temporal_key=temporal_key,
                )
                item_metadata = {
                    **base_metadata,
                    "prefu_ques": prefu,
                    "temporal_key": temporal_key,
                }

                existing = existing_by_domain_prefu.get((domain_key, prefu))
                if existing:
                    existing.axis = axis
                    existing.question_text = question.get("question_text", "")
                    existing.question_type = question.get("question_type", "multiple_choice")
                    existing.options = options
                    existing.item_metadata = item_metadata
                else:
                    db.session.add(
                        AssessmentItem(
                            framework_id=framework_id,
                            axis=axis,
                            question_text=question.get("question_text", ""),
                            question_type=question.get("question_type", "multiple_choice"),
                            options=options,
                            item_metadata=item_metadata,
                        )
                    )
                saved += 1

        return saved

    @staticmethod
    def _prefu_from_axis(axis: str) -> str:
        if "(Futuro)" in axis:
            return "F"
        if "(Presente)" in axis:
            return "P"
        return "P"

    @classmethod
    def _prefu_for_item(cls, item: AssessmentItem) -> str:
        metadata = item.item_metadata or {}
        prefu = str(metadata.get("prefu_ques") or "").upper()
        if prefu in ("P", "F"):
            return prefu
        return cls._prefu_from_axis(item.axis)

    @classmethod
    def _iter_block_questions(
        cls, block: dict[str, Any]
    ) -> list[tuple[str, str, dict[str, Any]]]:
        questions_map = block.get("assessment_questions")
        if isinstance(questions_map, dict):
            parsed: list[tuple[str, str, dict[str, Any]]] = []
            for temporal_key in TA_TEMPORAL_KEYS:
                question = questions_map.get(temporal_key)
                if isinstance(question, dict):
                    parsed.append((temporal_key, TA_PREFU_BY_TEMPORAL[temporal_key], question))
            if parsed:
                return parsed

        legacy = block.get("assessment_question")
        if isinstance(legacy, dict):
            return [("present", "P", legacy)]

        return []

    @classmethod
    def _sector_items_to_building_blocks(
        cls, items: list[AssessmentItem]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}

        for item in items:
            metadata = item.item_metadata or {}
            domain_key = str(metadata.get("domain_key") or cls._domain_key_for_item(item) or "ds")
            domain_name = str(metadata.get("domain_name") or domain_key)
            prefu = cls._prefu_for_item(item)
            temporal_key = "future" if prefu == "F" else "present"

            block = grouped.setdefault(
                domain_key,
                {
                    "domain_key": domain_key,
                    "domain_name": domain_name,
                    "block_name": metadata.get("block_name") or item.axis,
                    "block_description": metadata.get("block_description") or "",
                    "assessment_questions": {},
                },
            )
            block["assessment_questions"][temporal_key] = {
                "prefu_ques": prefu,
                "question_text": item.question_text,
                "question_type": item.question_type,
                "options": item.options or [],
            }

        return [grouped[key] for key, _ in OPERATIONAL_DOMAINS if key in grouped]

    @staticmethod
    def _domain_key_for_item(item: AssessmentItem) -> str | None:
        metadata = item.item_metadata or {}
        domain_key = metadata.get("domain_key")
        if domain_key:
            return str(domain_key)

        if " / " not in item.axis:
            return None
        right = item.axis.split(" / ", 1)[1]
        for suffix in (" (Presente)", " (Futuro)"):
            if right.endswith(suffix):
                right = right[: -len(suffix)]
        if " — " in right:
            return right.split(" — ", 1)[0].strip()
        return None

    @staticmethod
    def _sort_blocks_by_domain(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        order = {key: index for index, (key, _) in enumerate(OPERATIONAL_DOMAINS)}
        return sorted(
            blocks,
            key=lambda block: order.get(block.get("domain_key"), 999),
        )

    @staticmethod
    def _normalize_options(
        options: list[dict[str, Any]],
        *,
        temporal_key: str = "present",
    ) -> list[dict[str, Any]]:
        return normalize_sector_question_options(options or [], temporal_key=temporal_key)

    @staticmethod
    def _options_are_generic_fallback(options: list[dict[str, Any]], *, temporal_key: str) -> bool:
        """Detecta rubricas genéricas de fallback (não setoriais)."""
        if len(options) != 6:
            return True
        generic_descs = (
            PANELDX_FUTURO_GENERIC_DESC if temporal_key == "future" else PANELDX_PRESENTE_GENERIC_DESC
        )
        generic_hits = 0
        for option in options:
            desc = (
                option.get("desc_rubr") or option.get("description") or option.get("desc") or ""
            ).strip()
            grad = option.get("grad_rubr", option.get("weight", option.get("grad")))
            try:
                grad = int(grad)
            except (TypeError, ValueError):
                continue
            if desc == generic_descs.get(grad, ""):
                generic_hits += 1
        return generic_hits >= 4

    @staticmethod
    def _validate_assessment_question(
        question: Any,
        domain_key: str,
        *,
        temporal_label: str,
    ) -> None:
        if not isinstance(question, dict) or not str(question.get("question_text") or "").strip():
            raise ValueError(
                f"assessment_question inválida ou sem question_text no domínio "
                f"'{domain_key}' ({temporal_label})."
            )

        if question.get("question_type", "multiple_choice") != "multiple_choice":
            raise ValueError(
                f"assessment_question do domínio '{domain_key}' ({temporal_label}) "
                "deve ser multiple_choice."
            )

        prefu = str(question.get("prefu_ques") or "").upper()
        expected_prefu = "F" if temporal_label == "Futuro" else "P"
        if prefu and prefu != expected_prefu:
            raise ValueError(
                f"prefu_ques incorreto no domínio '{domain_key}' ({temporal_label}): "
                f"esperado '{expected_prefu}', recebido '{prefu}'."
            )

        options = question.get("options")
        if not isinstance(options, list) or len(options) != 6:
            raise ValueError(
                f"assessment_question do domínio '{domain_key}' ({temporal_label}) "
                "deve ter exatamente 6 options (grad 0-5)."
            )

        for index, option in enumerate(options):
            if not isinstance(option, dict):
                raise ValueError(
                    f"Option {index + 1} inválida no domínio '{domain_key}' ({temporal_label})."
                )
            label = (option.get("label") or option.get("label_rubr") or option.get("text") or "").strip()
            description = (
                option.get("description") or option.get("desc_rubr") or option.get("desc") or ""
            ).strip()
            if not label or not description:
                raise ValueError(
                    f"Option {index + 1} do domínio '{domain_key}' ({temporal_label}) "
                    "exige label e description (padrão PanelDX)."
                )

    @staticmethod
    def _normalize_sector_domain_keys(blocks: list[dict[str, Any]]) -> None:
        for block in blocks:
            raw_key = block.get("domain_key")
            if not is_valid_operational_domain_key(raw_key):
                allowed = ", ".join(sorted(CANONICAL_DOMAIN_KEYS))
                raise ValueError(
                    f"domain_key '{raw_key}' inválido na 5ª dimensão. "
                    f"Use exclusivamente ids canônicos: {allowed}."
                )
            canonical_key = normalize_domain_key(raw_key)
            block["domain_key"] = canonical_key
            if not block.get("domain_name") and canonical_key in DOMAIN_NAMES_BY_KEY:
                block["domain_name"] = DOMAIN_NAMES_BY_KEY[canonical_key]

    def _validate_sector_blocks(self, blocks: list[dict[str, Any]]) -> None:
        if not isinstance(blocks, list) or len(blocks) != 9:
            raise ValueError(
                "'building_blocks' deve conter exatamente 9 blocos (1 por domínio TA)."
            )

        self._normalize_sector_domain_keys(blocks)

        expected_keys = set(CANONICAL_DOMAIN_KEYS)
        found_keys: set[str] = set()
        for block in blocks:
            domain_key = block.get("domain_key")
            if domain_key not in expected_keys:
                raise ValueError(
                    f"domain_key inválido após normalização: {domain_key}. "
                    f"Esperado um de: {', '.join(sorted(expected_keys))}."
                )
            if domain_key in found_keys:
                raise ValueError(
                    f"domain_key duplicado: {domain_key}. Deve haver apenas um bloco por domínio."
                )
            found_keys.add(domain_key)

            questions_map = block.get("assessment_questions")
            if isinstance(questions_map, dict):
                for temporal_key in TA_TEMPORAL_KEYS:
                    temporal_label = TA_TEMPORAL_LABELS[temporal_key]
                    question = questions_map.get(temporal_key)
                    self._validate_assessment_question(
                        question,
                        str(domain_key),
                        temporal_label=temporal_label,
                    )
                continue

            if block.get("assessment_question"):
                raise ValueError(
                    f"Domínio '{domain_key}' usa formato legado. "
                    "Informe assessment_questions.present e assessment_questions.future."
                )
            raise ValueError(
                f"Domínio '{domain_key}' sem assessment_questions.present/future."
            )

        if found_keys != expected_keys:
            missing = expected_keys - found_keys
            raise ValueError(
                f"Cobertura incompleta da TA. Domínios sem bloco: {', '.join(sorted(missing))}"
            )

    def _validate_sector_payload(self, payload: dict[str, Any], expected_acronym: str) -> None:
        if "operational_dimension" not in payload:
            raise ValueError("JSON incompleto: 'operational_dimension' ausente.")

        op_dim = payload["operational_dimension"]
        if not isinstance(op_dim, dict):
            raise ValueError("'operational_dimension' deve ser um objeto.")

        acronym = (op_dim.get("acronym") or "").upper()
        if acronym and acronym != expected_acronym.upper():
            raise ValueError(
                f"Sigla esperada '{expected_acronym}', recebida '{acronym}'."
            )

        self._validate_sector_blocks(op_dim.get("building_blocks") or [])

    @staticmethod
    def _normalize_meta_building_blocks(payload: dict[str, Any]) -> None:
        """Mapeia campos meta-framework LeAction F para o schema PanelDX validável."""
        op_dim = payload.get("operational_dimension")
        if not isinstance(op_dim, dict):
            return

        blocks = op_dim.get("building_blocks")
        if not isinstance(blocks, list):
            return

        for block in blocks:
            if not isinstance(block, dict):
                continue

            title = (block.get("title") or "").strip()
            if title and not (block.get("block_name") or "").strip():
                block["block_name"] = title

            domain = (block.get("domain") or "").strip()
            if domain:
                mapped_key = LEACTION_F_TO_DOMAIN_KEY.get(domain)
                if not mapped_key:
                    for name, key in LEACTION_F_TO_DOMAIN_KEY.items():
                        if name.lower() == domain.lower():
                            mapped_key = key
                            block["domain"] = name
                            break
                if mapped_key and not block.get("domain_key"):
                    block["domain_key"] = mapped_key

            challenge = (block.get("challenge_addressed") or "").strip()
            if challenge and not (block.get("block_description") or "").strip():
                block["block_description"] = challenge

            if block.get("domain_key") and not block.get("domain_name"):
                canonical_key = normalize_domain_key(block.get("domain_key"))
                if canonical_key in DOMAIN_NAMES_BY_KEY:
                    block["domain_name"] = DOMAIN_NAMES_BY_KEY[canonical_key]

    @classmethod
    def _hydrate_sector_rubrics(cls, payload: dict[str, Any]) -> None:
        """Normaliza rubricas setoriais; rejeita fallback genérico sem conteúdo da IA."""
        op_dim = payload.get("operational_dimension")
        if not isinstance(op_dim, dict):
            return

        blocks = op_dim.get("building_blocks")
        if not isinstance(blocks, list):
            return

        for block in blocks:
            domain_key = block.get("domain_key", "?")
            questions_map = block.get("assessment_questions")
            if not isinstance(questions_map, dict):
                continue
            for temporal_key in TA_TEMPORAL_KEYS:
                question = questions_map.get(temporal_key)
                if not isinstance(question, dict):
                    continue
                raw_options = question.get("options") or []
                normalized = cls._normalize_options(
                    raw_options,
                    temporal_key=temporal_key,
                )
                if not raw_options:
                    raise ValueError(
                        f"Rubricas ausentes no domínio '{domain_key}' "
                        f"({TA_TEMPORAL_LABELS[temporal_key]}). "
                        "Regenere a proposta — cada pergunta setorial exige 6 options."
                    )
                if cls._options_are_generic_fallback(normalized, temporal_key=temporal_key):
                    raise ValueError(
                        f"Rubricas genéricas detectadas no domínio '{domain_key}' "
                        f"({TA_TEMPORAL_LABELS[temporal_key]}). "
                        "A IA deve gerar desc_rubr específicas ao setor em cada grad."
                    )
                question["options"] = normalized

    def _parse_ai_json(self, raw_text: str) -> dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise ValueError("A IA retornou resposta vazia.")

        cleaned = raw_text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL | re.IGNORECASE)
        if fence:
            cleaned = fence.group(1).strip()

        candidates: list[str] = [cleaned, _repair_ai_json_text(cleaned)]
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            snippet = cleaned[start : end + 1]
            candidates.extend(
                [
                    snippet,
                    _repair_ai_json_text(snippet),
                    _close_truncated_json(snippet),
                    _repair_ai_json_text(_close_truncated_json(snippet)),
                ]
            )

        last_error: json.JSONDecodeError | None = None
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            if isinstance(parsed, dict):
                return parsed

        detail = str(last_error) if last_error else "formato inválido"
        raise ValueError(
            "Não foi possível interpretar o JSON retornado pela IA "
            f"({detail}). Tente gerar a proposta novamente."
        )

    def _validate_proposal(self, proposal: dict[str, Any]) -> None:
        missing = [key for key in REQUIRED_ROOT_KEYS if key not in proposal]
        if missing:
            raise ValueError(f"JSON incompleto. Campos ausentes: {', '.join(missing)}.")

        manifest = proposal.get("manifest")
        if not isinstance(manifest, dict):
            raise ValueError("O campo 'manifest' deve ser um objeto.")
        if not manifest.get("name") or not manifest.get("descricao"):
            raise ValueError("O manifest deve conter 'name' e 'descricao'.")

        levels = proposal.get("maturity_levels")
        if not isinstance(levels, list) or len(levels) != 4:
            raise ValueError("'maturity_levels' deve ser uma lista com exatamente 4 níveis.")

        op_dim = proposal.get("operational_dimension")
        if not isinstance(op_dim, dict):
            raise ValueError("'operational_dimension' deve ser um objeto.")

        self._validate_sector_blocks(op_dim.get("building_blocks") or [])

    @staticmethod
    def _flatten_assessment_items(operational_dimension: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        acronym = operational_dimension.get("acronym", "XX")
        full_label = operational_dimension.get("full_label", operational_dimension.get("name", ""))
        for block in operational_dimension.get("building_blocks", []):
            domain_key = block.get("domain_key")
            domain_name = block.get("domain_name")
            for temporal_key, prefu, question in FrameworkBuilderService._iter_block_questions(block):
                temporal_label = TA_TEMPORAL_LABELS[temporal_key]
                items.append(
                    {
                        "axis": (
                            f"{acronym} — {full_label} / {domain_key} — {domain_name} "
                            f"({temporal_label})"
                        ),
                        "block_name": block.get("block_name"),
                        "block_description": block.get("block_description"),
                        "question_text": question.get("question_text"),
                        "question_type": question.get("question_type", "multiple_choice"),
                        "options": question.get("options", []),
                        "prefu_ques": prefu,
                    }
                )
        return items

    @staticmethod
    def _is_universal_axis(axis: str) -> bool:
        return axis.startswith(UNIVERSAL_AXIS_PREFIXES)

    @classmethod
    def _assessment_item_to_building_block(cls, item: AssessmentItem) -> dict[str, Any]:
        return cls._sector_items_to_building_blocks([item])[0]

    @classmethod
    def _default_maturity_options(cls) -> list[dict[str, Any]]:
        return default_maturity_options()

    @classmethod
    def _ensure_nine_building_blocks(
        cls, blocks: list[dict[str, Any]], op_meta: dict[str, Any]
    ) -> list[dict[str, Any]]:
        by_key: dict[str, dict[str, Any]] = {}
        for block in blocks:
            key = normalize_domain_key(block.get("domain_key"))
            if key:
                block["domain_key"] = key
                by_key[key] = block
        sector_label = op_meta.get("name") or "Setor"
        normalized: list[dict[str, Any]] = []

        for domain_key, domain_name in OPERATIONAL_DOMAINS:
            if domain_key in by_key:
                normalized.append(by_key[domain_key])
                continue

            normalized.append(
                {
                    "domain_key": domain_key,
                    "domain_name": domain_name,
                    "block_name": f"{domain_name} — {sector_label}",
                    "block_description": "",
                    "assessment_questions": {
                        "present": {
                            "prefu_ques": "P",
                            "question_text": (
                                f"Como está hoje a prática de {domain_name} no core operacional do setor?"
                            ),
                            "question_type": "multiple_choice",
                            "options": cls._default_maturity_options(),
                        },
                        "future": {
                            "prefu_ques": "F",
                            "question_text": (
                                f"Qual a perspectiva de evolução de {domain_name} no core operacional do setor?"
                            ),
                            "question_type": "multiple_choice",
                            "options": default_futuro_options(),
                        },
                    },
                }
            )

        return normalized

    @classmethod
    def _build_operational_dimension_from_blocks(
        cls,
        blocks: list[dict[str, Any]],
        metadata: dict[str, Any],
        framework: Framework,
    ) -> dict[str, Any]:
        op_name = metadata.get("operational_dimension_name") or framework.industry or "Sector Action"
        acronym = metadata.get("operational_dimension_acronym") or "XX"
        action_name = op_name
        full_label = op_name

        if " - " in op_name:
            parts = op_name.rsplit(" - ", 1)
            action_name = parts[0].strip()
            acronym = parts[1].strip() or acronym

        op_meta = {"name": action_name, "acronym": acronym, "full_label": full_label}
        return {
            "name": action_name,
            "acronym": acronym,
            "full_label": full_label,
            "description": metadata.get("operational_dimension", {}).get("description", ""),
            "building_blocks": cls._ensure_nine_building_blocks(blocks, op_meta),
        }

    @classmethod
    def _build_rules_metadata(
        cls,
        proposal: dict[str, Any],
        sector: str,
        acronym: str,
        full_label: str,
        op_dim: dict[str, Any],
        *,
        approval_status: str = APPROVAL_STATUS_APPROVED,
    ) -> dict[str, Any]:
        from app.data.legacy_framework_loader import (
            build_full_methodology_document,
            methodology_summary_counts,
        )

        manifest = proposal.get("manifest") or {}
        methodology_doc = build_full_methodology_document(operational_dimension=op_dim)
        return {
            "sector": sector,
            "manifest": manifest,
            "operational_dimension_acronym": acronym,
            "operational_dimension_name": full_label,
            "operational_dimension": op_dim,
            "universal_dimensions": proposal.get("universal_dimensions") or UNIVERSAL_DIMENSIONS,
            "research_sources": proposal.get("sources", []),
            "approval_status": approval_status,
            "ingestion_complete": approval_status == APPROVAL_STATUS_APPROVED,
            "methodology_document": methodology_doc,
            "methodology_counts": methodology_summary_counts(methodology_doc),
            "scale_min": 1,
            "scale_max": 4,
        }

    @staticmethod
    def _slugify_sector(sector: str) -> str:
        normalized = unicodedata.normalize("NFKD", sector)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
        return slug or "sector"

    def _framework_id_for_sector(self, sector: str) -> str:
        return f"{self._slugify_sector(sector)}-v1"

    def _sector_action_meta(self, sector: str) -> tuple[str, str]:
        key = sector.strip().lower()
        if key in SECTOR_ACTION_META:
            return SECTOR_ACTION_META[key]

        slug = self._slugify_sector(sector).replace("-", "")
        acronym = (slug[:2] or "SA").upper()
        action_name = f"{sector.strip().title()} Action"
        return acronym, action_name
