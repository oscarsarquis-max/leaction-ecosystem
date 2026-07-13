"""Agente Modulador TD — auditoria de evidência vs Definition of Done (padrão PanelDX)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from html import unescape
from typing import Any

from flask import g

from app.core.rbac import ROLE_SYSADMIN
from app.infrastructure.ai_client import invoke_claude
from app.models.td_models import TdSprint
from app.database.models import db


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _format_dod(criteria_dod: Any, fallback: str | None = None) -> str:
    if isinstance(criteria_dod, dict):
        required = criteria_dod.get("required") or []
        education = criteria_dod.get("context_education") or []
        lines: list[str] = []
        if required:
            lines.append("Obrigatórios:")
            lines.extend(f"- {item}" for item in required)
        if education:
            lines.append("Contexto / educação:")
            lines.extend(f"- {item}" for item in education)
        if lines:
            return "\n".join(lines)
    if isinstance(criteria_dod, list) and criteria_dod:
        return "\n".join(f"- {item}" for item in criteria_dod)
    return (fallback or "Sem critérios formalizados — audite o objetivo da sprint.").strip()


def _extract_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError("Resposta do Modulador não contém JSON válido.")


class TdModuladorService:
    """Avalia evidência de execução de sprint TD contra o DoD (espelho PanelDX)."""

    def evaluate(self, sprint_id: str, evidencia: str) -> dict[str, Any]:
        tenant_id = g.tenant_id
        try:
            sprint_uuid = uuid.UUID(str(sprint_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("ID de sprint inválido.") from exc

        sprint = TdSprint.query.filter_by(id=sprint_uuid).first()
        if not sprint:
            raise ValueError("Sprint não encontrada.")
        if sprint.tenant_id != tenant_id and getattr(g, "system_role", None) != ROLE_SYSADMIN:
            raise PermissionError("Sprint fora do tenant autenticado.")

        evidencia_limpa = _strip_html(evidencia)
        if len(evidencia_limpa) < 10:
            raise ValueError(
                "Descreva a evidência com mais detalhes antes de submeter ao Modulador."
            )

        goals = dict(sprint.goals_payload or {})
        dod_texto = _format_dod(goals.get("criteria_dod"), goals.get("desc_sprn") or sprint.description)

        system_prompt = (
            "Você é um Auditor de Qualidade extremamente rigoroso e cético. Seu papel é comparar a "
            "Evidência fornecida pelo usuário com o Definition of Done (Critérios de Aceite) da Sprint, "
            "exigindo PROVAS CONCRETAS para cada critério obrigatório. Responda sempre em português do Brasil.\n\n"
            "REGRAS INEGOCIÁVEIS:\n"
            "REGRA 1: Não acredite em declarações vagas do usuário (ex.: 'documento anexado', 'feito', "
            "'aprovado', 'concluído'). Afirmação sem prova material NÃO é evidência.\n"
            "REGRA 2: Se o Definition of Done (DoD) exigir um link, publicação ou portal, a evidência DEVE "
            "conter obrigatoriamente uma URL válida (começando com http:// ou https://). Sem URL = REPROVADO.\n"
            "REGRA 3: Se o DoD exigir aprovação formal, e-mail ou ata, a evidência DEVE conter a "
            "transcrição/cópia desse e-mail/ata no próprio texto. Apenas dizer 'foi aprovado' = REPROVADO.\n"
            "REGRA 4: Se faltar prova concreta para QUALQUER critério obrigatório do DoD, atribua nota "
            "menor que 50 e retorne o status 'Revisão Necessária'.\n\n"
            "A 'nota' (inteiro de 0 a 100) deve refletir o percentual de critérios obrigatórios efetivamente "
            "COMPROVADOS com prova material. Critério sem prova concreta NÃO conta como cumprido."
        )
        user_content = (
            f"TÍTULO DA SPRINT:\n{goals.get('name_sprn') or sprint.title or 'N/A'}\n\n"
            f"DESCRIÇÃO / OBJETIVO:\n{goals.get('objetivo') or sprint.description or goals.get('desc_sprn') or 'N/A'}\n\n"
            f"ENTREGÁVEL DE REFERÊNCIA:\n{goals.get('name_derv') or goals.get('deliverable_name') or 'N/A'} — "
            f"{goals.get('derv_defi') or 'sem definição adicional'}\n\n"
            f"DEFINITION OF DONE (CRITÉRIOS DE ACEITE):\n{dod_texto}\n\n"
            f"EVIDÊNCIA APRESENTADA PELO USUÁRIO:\n{evidencia_limpa}\n\n"
            "Audite a evidência critério a critério, aplicando as REGRAS INEGOCIÁVEIS. Retorne APENAS um JSON "
            "estrito, sem markdown e sem texto fora do objeto, no formato exato:\n"
            '{"status": "Aprovado" ou "Revisão Necessária", '
            '"nota": número inteiro de 0 a 100, '
            '"feedback": "parecer objetivo e construtivo", '
            '"pontos_fortes": ["..."], "pendencias": ["..."]}'
        )

        try:
            raw = invoke_claude(
                user_content,
                max_tokens=1500,
                system=system_prompt,
                temperature=0.2,
            )
            veredito = _extract_json(raw)
        except Exception as exc:
            raise RuntimeError(
                "O Modulador IA está temporariamente indisponível. Tente novamente em instantes."
            ) from exc

        try:
            nota = int(round(float(veredito.get("nota"))))
        except (TypeError, ValueError):
            nota = None
        if nota is not None:
            nota = max(0, min(100, nota))

        status_raw = (veredito.get("status") or "").strip().lower()
        aprovado = status_raw == "aprovado"
        pontos = veredito.get("pontos_fortes")
        pendencias = veredito.get("pendencias")
        resultado: dict[str, Any] = {
            "status": "Aprovado" if aprovado else "Revisão Necessária",
            "nota": nota,
            "feedback": (veredito.get("feedback") or "").strip(),
            "pontos_fortes": pontos if isinstance(pontos, list) else [],
            "pendencias": pendencias if isinstance(pendencias, list) else [],
        }

        dod_lower = dod_texto.lower()
        exige_url = any(
            p in dod_lower
            for p in ("link", "http", "url", "portal", "publica", "publicad", "publicaç")
        )
        tem_url = bool(re.search(r"https?://", evidencia_limpa))
        if exige_url and not tem_url:
            aprovado = False
            nota = min(nota, 45) if nota is not None else 40
            msg = (
                "O DoD exige link/publicação, mas nenhuma URL (http/https) "
                "foi encontrada na evidência."
            )
            if msg not in resultado["pendencias"]:
                resultado["pendencias"].insert(0, msg)

        if nota is None:
            nota = 80 if aprovado else 40
        if nota < 50:
            aprovado = False

        resultado["status"] = "Aprovado" if aprovado else "Revisão Necessária"
        resultado["nota"] = nota

        now = datetime.now(timezone.utc).isoformat()
        chat = list(goals.get("modulador_chat") or [])
        if not isinstance(chat, list):
            chat = []
        chat.append(
            {
                "role": "user",
                "content": evidencia_limpa,
                "at": now,
            }
        )
        chat.append(
            {
                "role": "modulador",
                "content": resultado.get("feedback") or resultado["status"],
                "veredito": resultado,
                "at": now,
            }
        )

        goals["evidencia_texto"] = evidencia
        goals["modulador_status"] = resultado["status"]
        goals["modulador_feedback"] = resultado
        goals["modulador_chat"] = chat[-40:]
        goals["realv_sprn"] = nota
        if aprovado:
            goals["stat_sprn"] = "concluida"
            from app.models.td_models import TdKanbanStage

            sprint.kanban_stage = TdKanbanStage.CONCLUIDA.value

        sprint.goals_payload = goals
        db.session.commit()
        db.session.refresh(sprint)

        return {
            "success": True,
            "sprint_id": str(sprint.id),
            "sprint_concluida": aprovado,
            "veredito": resultado,
            "modulador_status": resultado["status"],
            "nota": resultado["nota"],
            "feedback": resultado["feedback"],
            "pontos_fortes": resultado["pontos_fortes"],
            "pendencias": resultado["pendencias"],
            "sprint": sprint.to_dict(),
        }
