"""Motor de Gênese TD — Decision Engine PanelDX sobre Bedrock Claude."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, timedelta
from typing import Any

from flask import g

from app.core.journey_constants import (
    JOURNEY_CONCLUIDO,
    JOURNEY_ERRO_IA,
    JOURNEY_PENDENTE,
    JOURNEY_PROCESSANDO,
)
from app.core.sector_constants import DOMAIN_NAMES_PT, LEGACY_DOMAIN_ID_TO_KEY
from app.core.td_constants import (
    ASSESSMENT_DOMAIN_TO_TD,
    TD_AI_MAX_TOKENS,
    TD_GENESE_MAX_SPRINTS,
    TD_GENESE_ONDA1_ATIVAS,
    TD_GENESIS_OUTPUT_SCHEMA,
    TD_GENESIS_SYSTEM_CONTRACT,
    TD_OFFICIAL_DOMAINS,
    TD_OFFICIAL_DOMAINS_SET,
)
from app.database.models import AssessmentSubmission, Tenant, db
from app.infrastructure.ai_client import invoke_claude
from app.models.td_models import TdKanbanStage, TdOriginType, TdPlan, TdSprint
from app.services.client_journey_service import (
    build_journey_payload,
    set_journey_status,
)
from app.services.diagnostic_scoring_service import maturity_scores_snapshot
from app.services.operational_service import OperationalService
from app.services.td_framework_gap_service import (
    build_block_candidates,
    format_block_catalog_for_prompt,
    parse_block_id,
)

logger = logging.getLogger(__name__)

_GENESIS_PHASE_KEY = "_genesis_phase"


def _set_genesis_phase(tenant: Tenant, phase: str) -> None:
    ctx = dict(tenant.context_data or {})
    ctx[_GENESIS_PHASE_KEY] = phase
    tenant.context_data = ctx


def _clear_genesis_phase(tenant: Tenant) -> None:
    ctx = dict(tenant.context_data or {})
    if _GENESIS_PHASE_KEY in ctx:
        del ctx[_GENESIS_PHASE_KEY]
        tenant.context_data = ctx


def _extract_json_object(raw: str) -> dict[str, Any]:
    if raw is None:
        raise ValueError("Resposta vazia do modelo.")
    limpo = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", limpo, re.DOTALL | re.IGNORECASE)
    if fence:
        limpo = fence.group(1).strip()
    try:
        data = json.loads(limpo)
    except json.JSONDecodeError:
        start = limpo.find("{")
        end = limpo.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("IA não retornou JSON válido.")
        data = json.loads(limpo[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON da IA deve ser um objeto.")
    return data


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def resolve_td_domain(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text in TD_OFFICIAL_DOMAINS_SET:
        return text
    lower = text.lower()
    if lower in ASSESSMENT_DOMAIN_TO_TD:
        return ASSESSMENT_DOMAIN_TO_TD[lower]
    # chave canônica curta (ds, bm, …)
    if lower in ASSESSMENT_DOMAIN_TO_TD:
        return ASSESSMENT_DOMAIN_TO_TD[lower]
    for official in TD_OFFICIAL_DOMAINS:
        if official.lower() in lower or lower in official.lower():
            return official
    return None


class TdGenesisService:
    """Gera Plano + Sprints TD sob comando do usuário e avança a jornada."""

    def generate_plan(self, *, force: bool = True) -> dict[str, Any]:
        tenant_id = self._tenant_id()
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant não encontrado.")

        if not self._latest_completed_submission(tenant_id):
            raise ValueError(
                "É necessário concluir a avaliação PanelDX antes de gerar o plano de TD."
            )

        from app.services.client_journey_service import _context_is_complete

        if not _context_is_complete(tenant.context_data or {}):
            raise ValueError(
                "Preencha o contexto organizacional (Meus Dados) antes de gerar o plano de TD."
            )

        set_journey_status(tenant, JOURNEY_PENDENTE)
        _set_genesis_phase(tenant, "Preparando insumos do diagnóstico…")
        db.session.commit()

        try:
            set_journey_status(tenant, JOURNEY_PROCESSANDO)
            _set_genesis_phase(tenant, "Cruzando Bússola Presente × Futuro com gaps…")
            db.session.commit()

            survey_snapshot = self._build_survey_snapshot(tenant_id)
            submission = self._latest_completed_submission(tenant_id)
            block_candidates = (
                build_block_candidates(submission) if submission else []
            )
            survey_snapshot["block_candidates"] = block_candidates
            survey_snapshot["block_pairs_with_gap"] = len(block_candidates)
            impediments = self._collect_gemba_impediments()
            prompt = self._build_prompt(
                tenant, survey_snapshot, impediments, block_candidates
            )
            _set_genesis_phase(tenant, "Consultor LeAction analisando com Claude…")
            db.session.commit()
            raw = invoke_claude(prompt, max_tokens=TD_AI_MAX_TOKENS)
            ai_payload = _extract_json_object(raw)
            sprints_raw = self._normalize_sprints(
                ai_payload, survey_snapshot, impediments, block_candidates
            )
            _set_genesis_phase(tenant, "Materializando plano e sprints no Kanban…")
            db.session.commit()
            plan = self._materialize_plan(
                tenant_id=tenant_id,
                survey_snapshot=survey_snapshot,
                sprints_raw=sprints_raw,
                ai_payload=ai_payload,
            )

            set_journey_status(tenant, JOURNEY_CONCLUIDO)
            _clear_genesis_phase(tenant)
            tenant.has_active_project = True
            db.session.commit()

            return {
                "plan": plan.to_dict(include_sprints=True),
                "journey": build_journey_payload(tenant),
                "generated_count": len(plan.sprints),
                "message": "Plano de Transformação Digital gerado com sucesso.",
            }
        except Exception as exc:
            logger.exception("Falha na Gênese TD: %s", exc)
            db.session.rollback()
            tenant = db.session.get(Tenant, tenant_id)
            if tenant:
                set_journey_status(tenant, JOURNEY_ERRO_IA)
                _clear_genesis_phase(tenant)
                db.session.commit()
            raise

    def _build_survey_snapshot(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        submission = self._latest_completed_submission(tenant_id)
        scores = maturity_scores_snapshot(submission) if submission else {}
        pdom_pres = scores.get("pdom_pres") or {}
        pdom_fut = scores.get("pdom_fut") or {}
        pdom_gap = scores.get("pdom_gap") or {}

        aggregates: dict[str, dict[str, list[float]]] = {
            domain: {"pres": [], "fut": [], "gap": []} for domain in TD_OFFICIAL_DOMAINS
        }

        keys = set(map(str, pdom_pres.keys())) | set(map(str, pdom_gap.keys())) | set(
            map(str, pdom_fut.keys())
        )
        for key in keys:
            td_domain = self._map_score_key_to_td(key)
            if not td_domain:
                continue
            pres = _coerce_float(pdom_pres.get(key))
            fut = _coerce_float(pdom_fut.get(key))
            gap = _coerce_float(pdom_gap.get(key))
            if gap is None and pres is not None and fut is not None:
                gap = fut - pres
            if pres is not None:
                aggregates[td_domain]["pres"].append(pres)
            if fut is not None:
                aggregates[td_domain]["fut"].append(fut)
            if gap is not None:
                aggregates[td_domain]["gap"].append(gap)

        domains: list[dict[str, Any]] = []
        for domain in TD_OFFICIAL_DOMAINS:
            bucket = aggregates[domain]
            avg_pres = (
                sum(bucket["pres"]) / len(bucket["pres"]) if bucket["pres"] else None
            )
            avg_fut = sum(bucket["fut"]) / len(bucket["fut"]) if bucket["fut"] else None
            avg_gap = sum(bucket["gap"]) / len(bucket["gap"]) if bucket["gap"] else None
            if avg_gap is None and avg_pres is not None and avg_fut is not None:
                avg_gap = avg_fut - avg_pres
            # Prioridade: maior gap; se empatar/ausente, menor score presente
            priority_score = avg_gap if avg_gap is not None else (
                (5.0 - avg_pres) if avg_pres is not None else 0.0
            )
            domains.append(
                {
                    "domain": domain,
                    "score": round(avg_pres, 2) if avg_pres is not None else None,
                    "future": round(avg_fut, 2) if avg_fut is not None else None,
                    "gap": round(avg_gap, 2) if avg_gap is not None else None,
                    "priority_score": round(float(priority_score), 2),
                }
            )

        domains_sorted = sorted(
            domains,
            key=lambda d: (
                -(d["priority_score"] or 0),
                d["score"] if d["score"] is not None else 99,
            ),
        )
        top_gap_domains = [d["domain"] for d in domains_sorted[:2]]

        return {
            "domains": domains,
            "top_gaps": domains_sorted[:5],
            "priority_domains": top_gap_domains,
            "pdom_pres": pdom_pres,
            "pdom_fut": pdom_fut,
            "pdom_gap": pdom_gap,
            "submission_id": str(submission.id) if submission else None,
        }

    def _map_score_key_to_td(self, key: str) -> str | None:
        raw = str(key).strip()
        if raw.isdigit():
            canon = LEGACY_DOMAIN_ID_TO_KEY.get(int(raw))
            if canon:
                return ASSESSMENT_DOMAIN_TO_TD.get(canon)
        lower = raw.lower()
        if lower in ASSESSMENT_DOMAIN_TO_TD:
            return ASSESSMENT_DOMAIN_TO_TD[lower]
        # nome PT do assessment
        for canon, name in DOMAIN_NAMES_PT.items():
            if name.lower() == lower:
                return ASSESSMENT_DOMAIN_TO_TD.get(canon)
        return resolve_td_domain(raw)

    def _collect_gemba_impediments(self) -> list[dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=30)
        try:
            summary = OperationalService().reports_summary(
                start_date=start, end_date=end, site_id=None
            )
            return list(summary.get("consolidated_impediments") or [])
        except Exception as exc:
            logger.warning("Não foi possível agregar impeditivos Gemba: %s", exc)
            return []

    def _build_prompt(
        self,
        tenant: Tenant,
        survey_snapshot: dict[str, Any],
        impediments: list[dict[str, Any]],
        block_candidates: list[dict[str, Any]],
    ) -> str:
        context = tenant.context_data or {}
        priority = survey_snapshot.get("priority_domains") or []
        catalog = format_block_catalog_for_prompt(block_candidates)
        return f"""{TD_GENESIS_SYSTEM_CONTRACT}

TENANT: {tenant.name}
PRIORITY_DOMAINS (maior gap nos 6 domínios oficiais PanelDX): {json.dumps(priority, ensure_ascii=False)}

{catalog}

SURVEY_SNAPSHOT (escores agregados nos 6 domínios oficiais):
{json.dumps(survey_snapshot.get("domains"), ensure_ascii=False, indent=2)}

IMPEDITIVOS_DO_GEMBA (últimos 30 dias — falhas de meta operacional):
{json.dumps(impediments[:25], ensure_ascii=False, indent=2)}

CONTEXTO_INSTITUCIONAL:
{json.dumps({k: context.get(k) for k in ("dados_mercado", "dados_clientes", "clima_organizacional", "mercado_resumo", "dados_etnograficos", "clima_resumo") if context.get(k)}, ensure_ascii=False, indent=2)}

INSTRUÇÃO DE PRIORIZAÇÃO: Blocos de catálogo que possuam um Gap elevado E QUE, simultaneamente, resolvam uma dor explícita listada nos [IMPEDITIVOS_DO_GEMBA] têm prioridade absoluta. Utiliza o [CONTEXTO_INSTITUCIONAL] para garantir que a justificativa reflete o momento e o jargão da nossa organização.

CHAIN OF THOUGHT (obrigatório por sprint): Ao construir a justificativa, DEVES OBRIGATORIAMENTE preencher os campos '_analise_gap', '_analise_gemba' e '_analise_contexto' primeiro. Eles servem de raciocínio lógico para construíres o parágrafo final e maduro na 'justificativa_baseada_no_relatorio'.

SCHEMA DE OUTPUT (objeto JSON único — espelho do modal PanelDX; respeite as descriptions do schema):
{json.dumps(TD_GENESIS_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)}

CONSTRAINTS ADICIONAIS:
- Gere enriquecimento para os blocos do catálogo com gap F−P positivo (priorize maior gap).
- Cada sprint DEVE referenciar id_bloc existente no catálogo — NÃO invente blocos.
- Preencha sempre _analise_gap, _analise_gemba e _analise_contexto ANTES de justificativa_baseada_no_relatorio; a justificativa deve sintetizar as três análises num único parágrafo (sem tópicos).
- Use o contexto institucional para personalizar objetivo, DoD, atividades táticas e sobretudo a justificativa (triangulação obrigatória).
- Pelo menos 1 sprint gemba_driven=true atacando impeditivos do Gemba (se houver), sempre com id_bloc.
- Output: somente JSON válido, sem markdown.
"""

    def _normalize_sprints(
        self,
        ai_payload: dict[str, Any],
        survey_snapshot: dict[str, Any],
        impediments: list[dict[str, Any]],
        block_candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raw_list = ai_payload.get("sprints")
        if not isinstance(raw_list, list):
            raw_list = ai_payload.get("roadmap_estrategico") or []
        if not isinstance(raw_list, list):
            raw_list = []

        ai_by_block = {}
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            block_id = parse_block_id(
                item.get("id_bloc") or item.get("framework_block_id") or item.get("id_bloco")
            )
            if block_id:
                ai_by_block[block_id] = item

        if block_candidates:
            normalized = [
                self._sprint_from_block_candidate(
                    candidate,
                    ai_by_block.get(candidate["framework_block_id"]),
                    rank=index + 1,
                )
                for index, candidate in enumerate(block_candidates)
            ]
        else:
            priority_domains = list(survey_snapshot.get("priority_domains") or [])
            normalized = self._fallback_sprints(survey_snapshot, impediments, priority_domains)

        # Enriquecer / inserir sprint Gemba com bloco vinculado
        if not any(s["gemba_driven"] for s in normalized):
            gemba = self._build_gemba_sprint(impediments, block_candidates, survey_snapshot)
            if gemba:
                normalized.append(gemba)

        normalized.sort(
            key=lambda s: (
                0 if s.get("gemba_driven") else 1,
                -(s.get("gap_fp") or 0),
                s.get("priority_rank") or 999,
            )
        )
        for index, sprint in enumerate(normalized, start=1):
            sprint["priority_rank"] = index
            sprint["goals_payload"]["priority_rank"] = index

        return normalized

    def _sprint_from_block_candidate(
        self,
        candidate: dict[str, Any],
        ai_item: dict[str, Any] | None,
        *,
        rank: int,
    ) -> dict[str, Any]:
        dim_num = candidate.get("dimension_num") or "?"
        block_name = candidate.get("name_bloc") or "Bloco metodológico"
        default_title = f"[DIM {dim_num}] {block_name}"
        ai_item = ai_item or {}

        title = str(
            ai_item.get("nome_sprint") or ai_item.get("name_sprn") or default_title
        ).strip()[:255]
        if not title.startswith("[DIM"):
            title = default_title[:255]

        origin = str(ai_item.get("origin_type") or TdOriginType.BASELINE.value).strip()
        gemba_driven = bool(ai_item.get("gemba_driven")) or origin == (
            TdOriginType.KAIZEN_EMERGENT.value
        )
        if gemba_driven:
            origin = TdOriginType.KAIZEN_EMERGENT.value

        dod = ai_item.get("criteria_dod") if isinstance(ai_item.get("criteria_dod"), dict) else {}
        if not dod:
            dod = candidate.get("criteria_dod") or {}
        required = dod.get("required") if isinstance(dod.get("required"), list) else []
        education = (
            dod.get("context_education") if isinstance(dod.get("context_education"), list) else []
        )

        domain = resolve_td_domain(
            ai_item.get("paneldx_domain") or candidate.get("paneldx_domain")
        ) or candidate.get("paneldx_domain")

        description = str(
            ai_item.get("descricao")
            or ai_item.get("desc_sprn")
            or ai_item.get("objetivo")
            or candidate.get("desc_bloc")
            or ""
        ).strip() or None

        goals_payload = {
            "name_sprn": title,
            "desc_sprn": description or "",
            "objetivo": str(ai_item.get("objetivo") or description or "").strip(),
            "derv_defi": str(
                ai_item.get("derv_defi") or candidate.get("derv_defi") or ""
            ).strip(),
            "derv_comp": str(
                ai_item.get("derv_comp") or candidate.get("derv_comp") or ""
            ).strip(),
            "criteria_dod": {
                "required": [str(x) for x in required],
                "context_education": [str(x) for x in education],
            },
            "atividades_taticas": [
                str(x) for x in (ai_item.get("atividades_taticas") or []) if str(x).strip()
            ],
            "swot_type": str(ai_item.get("swot_type") or "Fraqueza").strip(),
            "swot_justification": str(
                ai_item.get("swot_justification")
                or ai_item.get("justificativa_baseada_no_relatorio")
                or ""
            ).strip(),
            "week_sprn": int(ai_item.get("week_sprn") or 2),
            "targv_sprn": int(ai_item.get("targv_sprn") or 10),
            "realv_sprn": 0,
            "metrics_scores": ai_item.get("metrics_scores")
            if isinstance(ai_item.get("metrics_scores"), dict)
            else {},
            "_analise_gap": str(ai_item.get("_analise_gap") or "").strip(),
            "_analise_gemba": str(ai_item.get("_analise_gemba") or "").strip(),
            "_analise_contexto": str(ai_item.get("_analise_contexto") or "").strip(),
            "justificativa_baseada_no_relatorio": str(
                ai_item.get("justificativa_baseada_no_relatorio") or ""
            ).strip(),
            "onda": str(ai_item.get("onda") or "Onda 1 — Prioridade Gap").strip(),
            "gemba_driven": gemba_driven,
            "priority_rank": rank,
            "paneldx_domain": domain,
            "framework_block_id": candidate["framework_block_id"],
            "framework_deliverable_id": candidate.get("framework_deliverable_id"),
            "legacy_id_bloc": candidate.get("legacy_id_bloc"),
            "name_bloc": candidate.get("name_bloc"),
            "name_derv": candidate.get("name_derv"),
            "dimension_name": candidate.get("dimension_name"),
            "domain_name": candidate.get("domain_name"),
            "dimension_num": candidate.get("dimension_num"),
            "gap_fp": candidate.get("gap_fp"),
            "score_presente": candidate.get("score_presente"),
            "score_futuro": candidate.get("score_futuro"),
        }

        return {
            "title": title,
            "description": description,
            "paneldx_domain": domain,
            "origin_type": origin,
            "gemba_driven": gemba_driven,
            "priority_rank": rank,
            "gap_fp": candidate.get("gap_fp"),
            "framework_block_id": candidate["framework_block_id"],
            "framework_deliverable_id": candidate.get("framework_deliverable_id"),
            "goals_payload": goals_payload,
        }

    def _fallback_sprints(
        self,
        survey_snapshot: dict[str, Any],
        impediments: list[dict[str, Any]],
        priority_domains: list[str],
    ) -> list[dict[str, Any]]:
        sprints: list[dict[str, Any]] = []
        for i, domain in enumerate(priority_domains[:2]):
            for j in range(2 if i == 0 else 1):
                rank = len(sprints) + 1
                title = f"Fechar Gap — {domain} (Prioridade {rank})"
                sprints.append(
                    {
                        "title": title,
                        "description": f"Sprint baseline para elevar maturidade em {domain}.",
                        "paneldx_domain": domain,
                        "origin_type": TdOriginType.BASELINE.value,
                        "gemba_driven": False,
                        "priority_rank": rank,
                        "goals_payload": self._default_goals(
                            title=title,
                            domain=domain,
                            objetivo=f"Reduzir o gap do domínio {domain}.",
                            rank=rank,
                            gemba=False,
                        ),
                    }
                )
        sprints.append(self._build_gemba_sprint(impediments, priority_domains))
        for domain in TD_OFFICIAL_DOMAINS:
            if len(sprints) >= 6:
                break
            if domain in priority_domains:
                continue
            rank = len(sprints) + 1
            title = f"Roadmap — {domain}"
            sprints.append(
                {
                    "title": title,
                    "description": f"Iniciativa estruturante no domínio {domain}.",
                    "paneldx_domain": domain,
                    "origin_type": TdOriginType.BASELINE.value,
                    "gemba_driven": False,
                    "priority_rank": rank,
                    "goals_payload": self._default_goals(
                        title=title,
                        domain=domain,
                        objetivo=f"Avançar capacidade digital em {domain}.",
                        rank=rank,
                        gemba=False,
                    ),
                }
            )
        return sprints

    def _build_gemba_sprint(
        self,
        impediments: list[dict[str, Any]],
        block_candidates: list[dict[str, Any]],
        survey_snapshot: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not impediments and not block_candidates:
            return None
        sample = impediments[0] if impediments else {}
        detail = (sample.get("impediment_details") or "falhas recorrentes de meta no Gemba")[:280]

        candidate = None
        for cand in block_candidates:
            if cand.get("paneldx_domain") == "Processos":
                candidate = cand
                break
        if not candidate and block_candidates:
            candidate = block_candidates[0]

        if candidate:
            sprint = self._sprint_from_block_candidate(candidate, None, rank=999)
            sprint["gemba_driven"] = True
            sprint["origin_type"] = TdOriginType.KAIZEN_EMERGENT.value
            sprint["title"] = f"[TÁTICO] [DIM {candidate.get('dimension_num')}] Eliminar causa raiz — Gemba"
            sprint["description"] = (
                f"Sprint estrutural contra impeditivos recorrentes: {detail}"
            )
            sprint["goals_payload"]["gemba_driven"] = True
            sprint["goals_payload"]["name_sprn"] = sprint["title"]
            sprint["goals_payload"]["desc_sprn"] = sprint["description"]
            sprint["goals_payload"]["objetivo"] = (
                "Padronizar contenção e prevenção das falhas operacionais recorrentes."
            )
            sprint["goals_payload"]["onda"] = "Gemba — Causa Raiz"
            sprint["goals_payload"]["swot_justification"] = detail
            sprint["gap_fp"] = (candidate.get("gap_fp") or 0) + 0.5
            sprint["goals_payload"]["gap_fp"] = sprint["gap_fp"]
            return sprint

        priority_domains = list(survey_snapshot.get("priority_domains") or ["Processos"])
        return self._build_gemba_sprint_legacy(impediments, priority_domains)

    def _build_gemba_sprint_legacy(
        self, impediments: list[dict[str, Any]], priority_domains: list[str]
    ) -> dict[str, Any]:
        domain = "Processos" if "Processos" in TD_OFFICIAL_DOMAINS_SET else priority_domains[0]
        sample = impediments[0] if impediments else {}
        detail = (sample.get("impediment_details") or "falhas recorrentes de meta no Gemba")[:280]
        title = "Eliminar causa raiz dos Impeditivos do Gemba"
        return {
            "title": title,
            "description": f"Sprint estrutural contra impeditivos recorrentes: {detail}",
            "paneldx_domain": domain,
            "origin_type": TdOriginType.KAIZEN_EMERGENT.value,
            "gemba_driven": True,
            "priority_rank": 4,
            "goals_payload": self._default_goals(
                title=title,
                domain=domain,
                objetivo="Padronizar contenção e prevenção das falhas operacionais recorrentes.",
                rank=4,
                gemba=True,
                swot_justification=detail,
            ),
        }

    def _default_goals(
        self,
        *,
        title: str,
        domain: str,
        objetivo: str,
        rank: int,
        gemba: bool,
        swot_justification: str = "",
    ) -> dict[str, Any]:
        return {
            "name_sprn": title,
            "desc_sprn": objetivo,
            "objetivo": objetivo,
            "derv_defi": f"Entregável verificável de melhoria em {domain}.",
            "derv_comp": "Facilitação Lean, leitura de indicadores e padronização operacional.",
            "criteria_dod": {
                "required": [
                    "Causa raiz documentada",
                    "Padrão operacional atualizado",
                    "Evidência de aderência no Gemba",
                ],
                "context_education": [
                    "Time capacitado no novo padrão",
                ],
            },
            "atividades_taticas": [
                "Mapear falhas recorrentes",
                "Definir contenção e prevenção",
                "Validar no Gemba",
            ],
            "swot_type": "Fraqueza",
            "swot_justification": swot_justification or objetivo,
            "week_sprn": 2,
            "targv_sprn": 10,
            "realv_sprn": 0,
            "metrics_scores": {},
            "_analise_gap": "",
            "_analise_gemba": "",
            "_analise_contexto": "",
            "justificativa_baseada_no_relatorio": objetivo,
            "onda": "Gemba — Causa Raiz" if gemba else "Onda 1 — Prioridade Gap",
            "gemba_driven": gemba,
            "priority_rank": rank,
            "paneldx_domain": domain,
        }

    def _materialize_plan(
        self,
        *,
        tenant_id: uuid.UUID,
        survey_snapshot: dict[str, Any],
        sprints_raw: list[dict[str, Any]],
        ai_payload: dict[str, Any],
    ) -> TdPlan:
        # Desativa planos anteriores
        previous = TdPlan.query.filter_by(tenant_id=tenant_id, is_active=True).all()
        for plan in previous:
            plan.is_active = False

        snapshot = dict(survey_snapshot)
        ordered = sorted(sprints_raw, key=lambda s: s.get("priority_rank") or 999)
        kanban_slots = 0
        exec_count = 0
        backlog_reserve: list[dict[str, Any]] = []

        for item in ordered:
            if kanban_slots < TD_GENESE_MAX_SPRINTS:
                if item.get("gemba_driven"):
                    item["_stage"] = TdKanbanStage.KAIZEN_ENTRADA.value
                    kanban_slots += 1
                elif exec_count < TD_GENESE_ONDA1_ATIVAS:
                    item["_stage"] = TdKanbanStage.EXECUCAO.value
                    exec_count += 1
                    kanban_slots += 1
                else:
                    item["_stage"] = TdKanbanStage.PLANEJADA.value
                    kanban_slots += 1
            else:
                item["_stage"] = TdKanbanStage.BACKLOG.value
                backlog_reserve.append(
                    {
                        "title": item.get("title"),
                        "framework_block_id": item.get("framework_block_id"),
                        "dimension_name": (item.get("goals_payload") or {}).get("dimension_name"),
                        "domain_name": (item.get("goals_payload") or {}).get("domain_name"),
                        "gap_fp": item.get("gap_fp"),
                    }
                )

        snapshot["ai_meta"] = {
            "sprint_count": len(ordered),
            "kanban_count": min(len(ordered), TD_GENESE_MAX_SPRINTS),
            "backlog_count": max(0, len(ordered) - TD_GENESE_MAX_SPRINTS),
            "priority_domains": survey_snapshot.get("priority_domains"),
        }
        if backlog_reserve:
            snapshot["backlog_geral_relatorio"] = backlog_reserve
        if isinstance(ai_payload.get("relatorio_inteligencia"), dict):
            snapshot["relatorio_inteligencia"] = ai_payload["relatorio_inteligencia"]

        plan = TdPlan(
            tenant_id=tenant_id,
            survey_snapshot=snapshot,
            is_active=True,
        )
        db.session.add(plan)
        db.session.flush()

        # Remove sprints órfãs de planos inativos do mesmo tenant (limpeza controlada)
        for old in previous:
            for sprint in list(old.sprints):
                db.session.delete(sprint)

        ordered = sorted(sprints_raw, key=lambda s: s.get("priority_rank") or 999)
        for index, item in enumerate(ordered):
            stage = item.pop("_stage", None) or self._stage_for_rank(index, item)
            goals = dict(item["goals_payload"])
            goals["ordr_sprn"] = index + 1
            goals["stat_sprn"] = self._panel_status_for_stage(stage)

            block_uuid = None
            derv_uuid = None
            raw_block = item.get("framework_block_id")
            raw_derv = item.get("framework_deliverable_id")
            if raw_block:
                try:
                    block_uuid = uuid.UUID(str(raw_block))
                except (TypeError, ValueError):
                    block_uuid = None
            if raw_derv:
                try:
                    derv_uuid = uuid.UUID(str(raw_derv))
                except (TypeError, ValueError):
                    derv_uuid = None

            sprint = TdSprint(
                tenant_id=tenant_id,
                plan_id=plan.id,
                title=item["title"],
                description=item.get("description"),
                paneldx_domain=item["paneldx_domain"],
                origin_type=item["origin_type"],
                kanban_stage=stage,
                goals_payload=goals,
                framework_block_id=block_uuid,
                framework_deliverable_id=derv_uuid,
                gap_fp=item.get("gap_fp"),
            )
            db.session.add(sprint)

        db.session.commit()
        db.session.refresh(plan)
        return plan

    @staticmethod
    def _stage_for_rank(index: int, item: dict[str, Any]) -> str:
        if item.get("gemba_driven") or item.get("origin_type") == TdOriginType.KAIZEN_EMERGENT.value:
            return TdKanbanStage.KAIZEN_ENTRADA.value
        if index < TD_GENESE_ONDA1_ATIVAS:
            return TdKanbanStage.EXECUCAO.value
        if index < TD_GENESE_MAX_SPRINTS:
            return TdKanbanStage.PLANEJADA.value
        return TdKanbanStage.BACKLOG.value

    @staticmethod
    def _panel_status_for_stage(stage: str) -> str:
        mapping = {
            TdKanbanStage.BACKLOG.value: "planejada_backlog",
            TdKanbanStage.KAIZEN_ENTRADA.value: "em_analise",
            TdKanbanStage.PLANEJADA.value: "planejada_backlog",
            TdKanbanStage.EXECUCAO.value: "em_andamento",
            TdKanbanStage.CONCLUIDA.value: "concluida",
        }
        return mapping.get(stage, "planejada_backlog")

    @staticmethod
    def _latest_completed_submission(tenant_id: uuid.UUID) -> AssessmentSubmission | None:
        return (
            AssessmentSubmission.query.filter_by(
                tenant_id=tenant_id,
                status="completed",
            )
            .order_by(
                AssessmentSubmission.evaluated_at.desc().nullslast(),
                AssessmentSubmission.created_at.desc(),
            )
            .first()
        )

    def _tenant_id(self) -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))
