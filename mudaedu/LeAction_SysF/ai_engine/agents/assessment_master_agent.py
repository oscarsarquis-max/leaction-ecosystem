"""Agente IA Master — assessment conversacional com dedução e cobertura total."""

import json
import os
import re
import sys
from typing import Any

import boto3
from botocore.config import Config

from ai_engine.prompts.assessment_master_templates import obter_system_prompt_ia_master

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_BOTO_CONFIG = Config(
    connect_timeout=8,
    read_timeout=45,
    retries={"max_attempts": 1},
)

FULL_ASSESSMENT_TOTAL = 162

# Palavras que indicam ausência de previsão/orçamento (rubrica Futuro = horizonte de adoção)
_FUTURO_NEG_QUALI = re.compile(
    r"(sem\s+verba|sem\s+previs[aã]o|sem\s+recurso|n[aã]o\s+dispon[ií]vel|n[aã]o\s+tem\s+recurso|"
    r"n[aã]o\s+est[aá]\s+no\s+(horizonte|planejamento)|fora\s+do\s+alcance|indispon[ií]vel|"
    r"invi[aá]vel|imposs[ií]vel|falta\s+de\s+verba|n[aã]o\s+or[cç]amentad|n[aã]o\s+previst|"
    r"investimento\s+n[aã]o\s+dispon)",
    re.IGNORECASE,
)
_FUTURO_POS_QUALI = re.compile(
    r"(or[cç]amentad|totalmente\s+previst|investimento\s+(confirmado|aprovado)|"
    r"pr[oó]xim[oa]s?\s+90\s+dias|ado[cç][aã]o\s+imediata|prioridade\s+total|curto\s+prazo\s+\(t\))",
    re.IGNORECASE,
)


class AssessmentMasterAgent:
    def __init__(self, db_manager):
        self.db = db_manager

    def _extrair_json(self, texto: str) -> dict:
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
            if inicio != -1 and fim > inicio:
                return json.loads(limpo[inicio : fim + 1])
            raise

    def _load_catalog(self, conn, is_mini: bool) -> list[dict]:
        questions = self.db.read_questions_structured_for_evaluation(conn)
        catalog = []
        for q in questions:
            is_ps = bool(q.get("presurvey_ques"))
            if is_mini and not is_ps:
                continue
            if not is_mini and is_ps:
                continue
            catalog.append(q)
        return catalog

    def _coverage(self, catalog: list[dict], saved_ids: set[int], is_mini: bool = False) -> dict:
        if is_mini:
            total = len(catalog) if catalog else 20
        else:
            total = len(catalog) if catalog else FULL_ASSESSMENT_TOTAL
            if catalog and len(catalog) < FULL_ASSESSMENT_TOTAL:
                total = FULL_ASSESSMENT_TOTAL
        answered = sum(1 for q in catalog if q["id_ques"] in saved_ids)
        pct = round((answered / total) * 100) if total else 0
        missing = [q for q in catalog if q["id_ques"] not in saved_ids]
        return {
            "answered": answered,
            "total": total,
            "percent": min(pct, 100),
            "missing_count": len(missing),
            "missing_ids": [q["id_ques"] for q in missing[:30]],
            "can_finalize": answered >= total and total > 0,
        }

    def _saved_answer_ids(self, conn, id_matu: int) -> set[int]:
        rows = self.db.read_surveys_by_maturity(conn, id_matu)
        return {r["id_ques"] for r in rows if r.get("id_ques") is not None}

    def _compact_question_for_llm(self, q: dict) -> dict:
        rubricas = [
            {
                "grad": r["grad_rubr"],
                "label": r.get("label_rubr") or f"Nível {r['grad_rubr']}",
            }
            for r in (q.get("rubricas") or [])
        ]
        return {
            "id_ques": q["id_ques"],
            "desc": (q.get("desc_ques") or "")[:220],
            "prefu": q.get("prefu_ques"),
            "dim": q.get("name_dime"),
            "dom": q.get("name_doma"),
            "rubricas": rubricas,
        }

    def _validate_answer(self, ans: dict, catalog_by_id: dict) -> dict | None:
        qid = ans.get("id_ques")
        if qid is None or qid not in catalog_by_id:
            return None
        q = catalog_by_id[qid]
        grad = ans.get("grad_ques")
        if grad is not None:
            valid_grads = {r["grad_rubr"] for r in (q.get("rubricas") or [])}
            try:
                grad = int(grad)
            except (TypeError, ValueError):
                return None
            if grad not in valid_grads:
                return None
        return {
            "id_ques": int(qid),
            "id_dime": q["id_dime"],
            "id_doma": q["id_doma"],
            "grad_ques": grad,
            "quali_ques": (ans.get("quali_ques") or ans.get("rubric_label") or "")[:2000],
            "prefu_ques": q.get("prefu_ques"),
        }

    def _is_futuro_horizon_rubric(self, q: dict) -> bool:
        """Questões Futuro com rubrica de horizonte de adoção (não maturidade)."""
        if str(q.get("prefu_ques")).upper() != "F":
            return False
        blob = " ".join(
            f"{r.get('label_rubr', '')} {r.get('desc_rubr', '')}"
            for r in (q.get("rubricas") or [])
        ).lower()
        return "prazo" in blob or "previsão" in blob or "previsao" in blob

    def _futuro_coherence_issue(self, answer: dict, question: dict) -> str | None:
        """Retorna motivo de rejeição se grad_ques e quali_ques forem incoerentes (Futuro)."""
        if not self._is_futuro_horizon_rubric(question):
            return None

        grad = answer.get("grad_ques")
        quali = (answer.get("quali_ques") or "").strip()
        if grad is None or not quali:
            return None

        try:
            g = int(grad)
        except (TypeError, ValueError):
            return None

        quali_l = quali.lower()
        has_neg = bool(_FUTURO_NEG_QUALI.search(quali_l))
        has_pos = bool(_FUTURO_POS_QUALI.search(quali_l))

        rub_by_grad = {
            int(r["grad_rubr"]): r.get("label_rubr") or f"Nível {r['grad_rubr']}"
            for r in (question.get("rubricas") or [])
            if r.get("grad_rubr") is not None
        }
        rub_label = rub_by_grad.get(g, str(g))

        # Nota alta (orçada/curto prazo) + texto negando verba/previsão
        if g >= 3 and has_neg and not has_pos:
            return (
                f"Questão {answer['id_ques']}: nota {g} ({rub_label}) indica adoção prevista/orçada, "
                f"mas o quali_ques nega verba ou previsão."
            )

        # Sem previsão + texto afirmando orçamento/adoção imediata
        if g == 0 and has_pos and not has_neg:
            return (
                f"Questão {answer['id_ques']}: nota 0 (Sem Previsão) conflita com quali_ques "
                f"que indica adoção prevista ou orçada."
            )

        # Horizonte longo/parcial + texto de prioridade imediata orçada
        if g <= 2 and has_pos and re.search(
            r"(or[cç]amentad|90\s+dias|imediata|curto\s+prazo\s+\(t\))", quali_l
        ):
            return (
                f"Questão {answer['id_ques']}: nota {g} ({rub_label}) é horizonte longo/parcial, "
                f"mas o quali_ques descreve adoção rápida ou orçada."
            )

        return None

    def _validate_answer_for_persist(
        self, ans: dict, catalog_by_id: dict
    ) -> tuple[dict | None, str | None]:
        validated = self._validate_answer(ans, catalog_by_id)
        if not validated:
            return None, "nota inválida ou fora da rubrica"
        issue = self._futuro_coherence_issue(validated, catalog_by_id[validated["id_ques"]])
        if issue:
            print(f"⚠️ [IA Master] Coerência Futuro rejeitada: {issue}", file=sys.stderr)
            return None, issue
        return validated, None

    def _persist_answers(self, conn, id_matu: int, answers: list[dict]) -> int:
        if not answers:
            return 0
        cur = conn.cursor()
        saved = 0
        try:
            for a in answers:
                cur.execute(
                    "SELECT id_surv FROM public.ctdi_surv WHERE id_matu = %s AND id_ques = %s",
                    (id_matu, a["id_ques"]),
                )
                row = cur.fetchone()
                quali = a.get("quali_ques") or ""
                if row:
                    cur.execute(
                        """UPDATE public.ctdi_surv
                           SET grad_ques = %s, quali_ques = %s
                           WHERE id_matu = %s AND id_ques = %s""",
                        (a["grad_ques"], quali, id_matu, a["id_ques"]),
                    )
                else:
                    cur.execute(
                        """INSERT INTO public.ctdi_surv
                           (id_matu, id_ques, id_dime, id_doma, grad_ques, quali_ques)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            id_matu,
                            a["id_ques"],
                            a["id_dime"],
                            a["id_doma"],
                            a["grad_ques"],
                            quali,
                        ),
                    )
                saved += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
        return saved

    def _build_context_payload(
        self,
        catalog: list[dict],
        saved_ids: set[int],
        coverage: dict,
        history: list[dict],
        user_message: str,
        action: str,
    ) -> str:
        missing = [q for q in catalog if q["id_ques"] not in saved_ids]
        missing_compact = [self._compact_question_for_llm(q) for q in missing[:40]]
        answered_sample = [
            self._compact_question_for_llm(q)
            for q in catalog
            if q["id_ques"] in saved_ids
        ][-15:]

        hist_text = ""
        for msg in (history or [])[-10:]:
            role = msg.get("role", "user")
            content = (msg.get("content") or "")[:800]
            hist_text += f"\n[{role.upper()}]: {content}"

        return (
            f"AÇÃO DO SISTEMA: {action}\n"
            f"COBERTURA: {coverage['answered']}/{coverage['total']} ({coverage['percent']}%)\n"
            f"INDICADORES FALTANTES: {coverage['missing_count']}\n\n"
            f"HISTÓRICO RECENTE:{hist_text or ' (início da partida)'}\n\n"
            f"MENSAGEM ATUAL DO GESTOR:\n{user_message or '(início — cumprimente e faça a pergunta de ancoragem)'}\n\n"
            f"AMOSTRA JÁ RESPONDIDOS (referência): {json.dumps(answered_sample, ensure_ascii=False)}\n\n"
            f"PRÓXIMOS INDICADORES SEM RESPOSTA (use ids exatos ao deduzir): "
            f"{json.dumps(missing_compact, ensure_ascii=False)}"
        )

    def _call_bedrock(self, system: str, user_content: str) -> dict:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=BEDROCK_REGION,
            config=BEDROCK_BOTO_CONFIG,
        )
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.55,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            }
        )
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        raw = json.loads(response["body"].read())["content"][0]["text"]
        return self._extrair_json(raw)

    def _fallback_turn(
        self,
        catalog: list[dict],
        saved_ids: set[int],
        coverage: dict,
        user_message: str,
        action: str,
        is_mini: bool,
    ) -> dict:
        missing = [q for q in catalog if q["id_ques"] not in saved_ids]
        nome = "Gestor"

        if action == "start" or not user_message.strip():
            return {
                "reply": (
                    f"Olá, {nome}! Sou o IA Master — seu consultor estratégico nesta jornada. "
                    "Vamos mapear sua escola com precisão, em poucas rodadas inteligentes. "
                    "Para começar: qual é o porte da sua instituição (nº de alunos) "
                    "e qual a principal dor operacional hoje?"
                ),
                "microcopy_badge": "Partida iniciada",
                "phase": "anchor",
                "macro_turn": 1,
                "interaction_type": "question",
                "requires_confirmation": False,
                "pending_deduction": None,
                "direct_answers": [],
            }

        if action == "confirm_deduction":
            return {
                "reply": "Perfeito — registrei o bloco deduzido. Vamos ao próximo insight estratégico.",
                "microcopy_badge": "Ponto para você",
                "phase": "present",
                "macro_turn": 2,
                "interaction_type": "question",
                "requires_confirmation": False,
                "pending_deduction": None,
                "direct_answers": [],
            }

        if missing and coverage["missing_count"] > 0:
            q = missing[0]
            prefu = "Presente" if str(q.get("prefu_ques")).upper() == "P" else "Futuro"
            return {
                "reply": (
                    f"Análise precisa. Falta pouco para o relatório — preciso ancorar o indicador "
                    f"de {prefu}: «{(q.get('desc_ques') or '')[:120]}...» "
                    "Em uma escala prática, como você classificaria hoje (1=incipiente, 5=excelente)?"
                ),
                "microcopy_badge": f"{coverage['percent']}% concluído",
                "phase": "gap_fill" if coverage["percent"] >= 70 else "present",
                "macro_turn": min(6, 2 + coverage["answered"] // 30),
                "interaction_type": "gap_single",
                "requires_confirmation": False,
                "pending_deduction": None,
                "direct_answers": [],
            }

        return {
            "reply": (
                "Excelente! Todos os indicadores foram mapeados. "
                "Seu relatório de gaps está pronto para consolidação — pode finalizar o assessment."
            ),
            "microcopy_badge": "100% completo",
            "phase": "complete",
            "macro_turn": 6,
            "interaction_type": "closing",
            "requires_confirmation": False,
            "pending_deduction": None,
            "direct_answers": [],
        }

    def process_turn(
        self,
        conn,
        id_matu: int,
        user_message: str = "",
        action: str = "message",
        history: list[dict] | None = None,
        pending_answers: list[dict] | None = None,
        is_mini: bool = False,
    ) -> dict[str, Any]:
        history = history or []
        catalog = self._load_catalog(conn, is_mini)
        catalog_by_id = {q["id_ques"]: q for q in catalog}
        saved_ids = self._saved_answer_ids(conn, id_matu)
        coverage = self._coverage(catalog, saved_ids, is_mini)

        applied_count = 0
        coherence_rejections: list[str] = []
        if action == "confirm_deduction" and pending_answers:
            validated = []
            for raw in pending_answers:
                v, reason = self._validate_answer_for_persist(raw, catalog_by_id)
                if v:
                    validated.append(v)
                elif reason:
                    coherence_rejections.append(reason)
            applied_count = self._persist_answers(conn, id_matu, validated)
            saved_ids = self._saved_answer_ids(conn, id_matu)
            coverage = self._coverage(catalog, saved_ids, is_mini)
            user_message = user_message or "Confirmo — acertou em cheio."

        total_q = len(catalog) if catalog else (20 if is_mini else FULL_ASSESSMENT_TOTAL)
        system = obter_system_prompt_ia_master(is_mini, total_q)
        user_content = self._build_context_payload(
            catalog, saved_ids, coverage, history, user_message, action
        )

        # Início e fallback local — resposta imediata sem esperar Bedrock
        if action in ("start",):
            parsed = self._fallback_turn(
                catalog, saved_ids, coverage, user_message, action, is_mini
            )
        else:
            try:
                parsed = self._call_bedrock(system, user_content)
            except Exception as err:
                print(f"⚠️ IA Master fallback: {err}", file=sys.stderr)
                parsed = self._fallback_turn(
                    catalog, saved_ids, coverage, user_message, action, is_mini
                )

        direct = []
        if not parsed.get("requires_confirmation"):
            for raw in parsed.get("direct_answers") or []:
                v, reason = self._validate_answer_for_persist(raw, catalog_by_id)
                if v:
                    direct.append(v)
                elif reason:
                    coherence_rejections.append(reason)
            if direct:
                applied_count += self._persist_answers(conn, id_matu, direct)
                saved_ids = self._saved_answer_ids(conn, id_matu)
                coverage = self._coverage(catalog, saved_ids, is_mini)

        pending = parsed.get("pending_deduction")
        pending_validated = []
        if pending and isinstance(pending, dict):
            for raw in pending.get("answers") or []:
                v, reason = self._validate_answer_for_persist(raw, catalog_by_id)
                if v:
                    pending_validated.append(v)
                elif reason:
                    coherence_rejections.append(reason)
            pending["answers"] = pending_validated
            pending["count"] = len(pending_validated)
            if coherence_rejections:
                pending["coherence_warnings"] = coherence_rejections[:8]

        reply = parsed.get("reply") or ""
        if coherence_rejections and action == "confirm_deduction":
            n_rej = len(coherence_rejections)
            reply += (
                f"\n\n⚠️ {n_rej} indicador(es) de Futuro foram descartados por incoerência "
                f"entre nota e justificativa (ex.: nota de adoção orçada com texto «sem verba»). "
                f"Peça ao gestor para confirmar o horizonte real de cada item."
            )

        return {
            "status": "ok",
            "reply": reply,
            "microcopy_badge": parsed.get("microcopy_badge") or "IA Master",
            "phase": parsed.get("phase") or "present",
            "macro_turn": parsed.get("macro_turn") or 1,
            "interaction_type": parsed.get("interaction_type") or "question",
            "requires_confirmation": bool(parsed.get("requires_confirmation")) and len(pending_validated) > 0,
            "pending_deduction": pending if pending_validated else None,
            "coverage": coverage,
            "answers_applied": applied_count,
            "can_finalize": coverage["can_finalize"],
            "coherence_rejections": coherence_rejections[:12],
        }

    def get_coverage(self, conn, id_matu: int, is_mini: bool = False) -> dict:
        catalog = self._load_catalog(conn, is_mini)
        saved_ids = self._saved_answer_ids(conn, id_matu)
        return self._coverage(catalog, saved_ids, is_mini)


def analisar_telemetria_esim(payload_dict: dict) -> dict:
    """Ponte desacoplada: telemetria eSIM → IA Master Executiva (Bedrock).

    Catálogo resolvido em esim_eventos_catalog (sem arquivo estático).
    """
    from integrations.esim.catalog import esim_buscar_catalogo
    from integrations.esim.schemas import esim_parse_telemetry_payload
    from integrations.esim.telemetry_agent import esim_analisar_anomalia_telemetria

    payload = esim_parse_telemetry_payload(payload_dict)
    catalog = esim_buscar_catalogo(payload.codigo_evento)
    if catalog is None:
        raise ValueError(
            f"codigo_evento '{payload.codigo_evento}' ausente de esim_eventos_catalog."
        )
    return esim_analisar_anomalia_telemetria(
        payload,
        codigo_evento=catalog.codigo_evento,
        dimensao_fixada=catalog.dimensao_fixada,
        dominio_fixado=catalog.dominio_fixado,
        blocos_candidatos_restritos=list(catalog.blocos_candidatos),
        interpretacao_leaction=catalog.descricao_tecnica,
        catalog_id=catalog.id,
    )


def analisar_telemetria_basemobile(payload_dict: dict) -> dict:
    """Alias legado — Base Mobile."""
    return analisar_telemetria_esim(payload_dict)
