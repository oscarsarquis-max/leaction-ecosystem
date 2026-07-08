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

logger = logging.getLogger(__name__)


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

        set_journey_status(tenant, JOURNEY_PENDENTE)
        db.session.commit()

        try:
            set_journey_status(tenant, JOURNEY_PROCESSANDO)
            db.session.commit()

            survey_snapshot = self._build_survey_snapshot(tenant_id)
            impediments = self._collect_gemba_impediments()
            prompt = self._build_prompt(tenant, survey_snapshot, impediments)
            raw = invoke_claude(prompt, max_tokens=TD_AI_MAX_TOKENS)
            ai_payload = _extract_json_object(raw)
            sprints_raw = self._normalize_sprints(ai_payload, survey_snapshot, impediments)
            plan = self._materialize_plan(
                tenant_id=tenant_id,
                survey_snapshot=survey_snapshot,
                sprints_raw=sprints_raw,
                ai_payload=ai_payload,
            )

            set_journey_status(tenant, JOURNEY_CONCLUIDO)
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
    ) -> str:
        context = tenant.context_data or {}
        priority = survey_snapshot.get("priority_domains") or []
        return f"""{TD_GENESIS_SYSTEM_CONTRACT}

TENANT: {tenant.name}
PRIORITY_DOMAINS (os dois de maior gap / menor pontuação — as 3 primeiras sprints DEVEM pertencer a estes): {json.dumps(priority, ensure_ascii=False)}

SURVEY_SNAPSHOT (escores agregados nos 6 domínios oficiais):
{json.dumps(survey_snapshot.get("domains"), ensure_ascii=False, indent=2)}

IMPEDITIVOS_DO_GEMBA (últimos 30 dias — falhas de meta operacional):
{json.dumps(impediments[:25], ensure_ascii=False, indent=2)}

CONTEXTO_INSTITUCIONAL:
{json.dumps({k: context.get(k) for k in ("dados_mercado", "dados_clientes", "clima_organizacional", "mercado_resumo", "dados_etnograficos", "clima_resumo") if context.get(k)}, ensure_ascii=False, indent=2)}

SCHEMA DE OUTPUT (objeto JSON único — espelho do modal de execução de Sprint PanelDX):
{{
  "sprints": [
    {{
      "nome_sprint": "string",
      "paneldx_domain": "Estratégia|Cultura|Processos|Tecnologia|Dados|Clientes",
      "origin_type": "baseline|kaizen_emergent",
      "objetivo": "string",
      "descricao": "string",
      "justificativa_baseada_no_relatorio": "string",
      "derv_defi": "definição do entregável",
      "derv_comp": "competências necessárias",
      "criteria_dod": {{
        "required": ["item obrigatório"],
        "context_education": ["item contextual"]
      }},
      "atividades_taticas": ["atividade 1", "atividade 2"],
      "swot_type": "Fraqueza",
      "swot_justification": "string",
      "week_sprn": 2,
      "targv_sprn": 10,
      "priority_rank": 1,
      "gemba_driven": false,
      "onda": "Onda 1 — Prioridade Gap"
    }}
  ]
}}

CONSTRAINTS ADICIONAIS:
- Gere entre 6 e {TD_GENESE_MAX_SPRINTS} sprints.
- As sprints com priority_rank 1, 2 e 3 DEVEM ter paneldx_domain em {json.dumps(priority, ensure_ascii=False)}.
- Pelo menos 1 sprint com gemba_driven=true e origin_type="kaizen_emergent" atacando a causa raiz dos Impeditivos do Gemba (se a lista estiver vazia, crie 1 sprint estrutural de Processos/Cultura para padronizar a rotina do Gemba).
- Cada sprint DEVE preencher os campos do modal PanelDX (derv_defi, derv_comp, criteria_dod, atividades_taticas, swot_*).
- Output: somente JSON válido, sem markdown.
"""

    def _normalize_sprints(
        self,
        ai_payload: dict[str, Any],
        survey_snapshot: dict[str, Any],
        impediments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raw_list = ai_payload.get("sprints")
        if not isinstance(raw_list, list):
            raw_list = ai_payload.get("roadmap_estrategico") or []
        if not isinstance(raw_list, list):
            raise ValueError("Payload da IA sem lista de sprints.")

        priority_domains = list(survey_snapshot.get("priority_domains") or [])
        if len(priority_domains) < 2:
            priority_domains = [d["domain"] for d in (survey_snapshot.get("top_gaps") or [])[:2]]
        if not priority_domains:
            priority_domains = ["Processos", "Tecnologia"]

        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(raw_list):
            if not isinstance(item, dict):
                continue
            title = str(
                item.get("nome_sprint")
                or item.get("name_sprn")
                or item.get("title")
                or ""
            ).strip()
            if not title:
                continue
            domain = resolve_td_domain(
                item.get("paneldx_domain") or item.get("dominio") or item.get("domain")
            )
            if not domain:
                domain = priority_domains[index % len(priority_domains)]
            origin = str(item.get("origin_type") or TdOriginType.BASELINE.value).strip()
            if origin not in (
                TdOriginType.BASELINE.value,
                TdOriginType.KAIZEN_EMERGENT.value,
            ):
                origin = TdOriginType.BASELINE.value
            gemba_driven = bool(item.get("gemba_driven")) or origin == (
                TdOriginType.KAIZEN_EMERGENT.value
            )
            if gemba_driven:
                origin = TdOriginType.KAIZEN_EMERGENT.value

            rank = item.get("priority_rank")
            try:
                rank = int(rank) if rank is not None else index + 1
            except (TypeError, ValueError):
                rank = index + 1

            dod = item.get("criteria_dod") if isinstance(item.get("criteria_dod"), dict) else {}
            required = dod.get("required") if isinstance(dod.get("required"), list) else []
            education = (
                dod.get("context_education")
                if isinstance(dod.get("context_education"), list)
                else []
            )

            normalized.append(
                {
                    "title": title[:255],
                    "description": str(
                        item.get("descricao")
                        or item.get("desc_sprn")
                        or item.get("objetivo")
                        or item.get("justificativa_baseada_no_relatorio")
                        or ""
                    ).strip()
                    or None,
                    "paneldx_domain": domain,
                    "origin_type": origin,
                    "gemba_driven": gemba_driven,
                    "priority_rank": rank,
                    "goals_payload": {
                        "name_sprn": title,
                        "desc_sprn": str(
                            item.get("descricao") or item.get("desc_sprn") or ""
                        ).strip(),
                        "objetivo": str(
                            item.get("objetivo") or item.get("descricao") or ""
                        ).strip(),
                        "derv_defi": str(item.get("derv_defi") or "").strip(),
                        "derv_comp": str(item.get("derv_comp") or "").strip(),
                        "criteria_dod": {
                            "required": [str(x) for x in required],
                            "context_education": [str(x) for x in education],
                        },
                        "atividades_taticas": [
                            str(x)
                            for x in (item.get("atividades_taticas") or [])
                            if str(x).strip()
                        ],
                        "swot_type": str(item.get("swot_type") or "Fraqueza").strip(),
                        "swot_justification": str(
                            item.get("swot_justification")
                            or item.get("justificativa_baseada_no_relatorio")
                            or ""
                        ).strip(),
                        "week_sprn": int(item.get("week_sprn") or 2),
                        "targv_sprn": int(item.get("targv_sprn") or 10),
                        "realv_sprn": 0,
                        "metrics_scores": item.get("metrics_scores")
                        if isinstance(item.get("metrics_scores"), dict)
                        else {},
                        "justificativa_baseada_no_relatorio": str(
                            item.get("justificativa_baseada_no_relatorio") or ""
                        ).strip(),
                        "onda": str(item.get("onda") or "").strip(),
                        "gemba_driven": gemba_driven,
                        "priority_rank": rank,
                        "paneldx_domain": domain,
                    },
                }
            )

        if not normalized:
            normalized = self._fallback_sprints(survey_snapshot, impediments, priority_domains)

        # Enforce: first 3 belong to the two priority domains
        normalized.sort(key=lambda s: s["priority_rank"])
        for i in range(min(3, len(normalized))):
            if normalized[i]["paneldx_domain"] not in priority_domains:
                normalized[i]["paneldx_domain"] = priority_domains[i % len(priority_domains)]
                normalized[i]["goals_payload"]["paneldx_domain"] = normalized[i][
                    "paneldx_domain"
                ]

        # Enforce at least one Gemba structural sprint
        if not any(s["gemba_driven"] for s in normalized):
            gemba = self._build_gemba_sprint(impediments, priority_domains)
            normalized.insert(min(3, len(normalized)), gemba)

        return normalized[:TD_GENESE_MAX_SPRINTS]

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
        snapshot["ai_meta"] = {
            "sprint_count": len(sprints_raw),
            "priority_domains": survey_snapshot.get("priority_domains"),
        }
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

        ordered = sorted(sprints_raw, key=lambda s: s["priority_rank"])
        for index, item in enumerate(ordered):
            stage = self._stage_for_rank(index, item)
            goals = dict(item["goals_payload"])
            goals["ordr_sprn"] = index + 1
            goals["stat_sprn"] = self._panel_status_for_stage(stage)
            sprint = TdSprint(
                tenant_id=tenant_id,
                plan_id=plan.id,
                title=item["title"],
                description=item.get("description"),
                paneldx_domain=item["paneldx_domain"],
                origin_type=item["origin_type"],
                kanban_stage=stage,
                goals_payload=goals,
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
        if index < TD_GENESE_ONDA1_ATIVAS + 4:
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
