"""Camadas determinísticas de proteção. Sem segundo gateway."""

from __future__ import annotations

import os
import re

from app.config import get_settings
from app.modules.ai_orchestration.gateway import GatewayError
from app.modules.ai_orchestration.settings import BedrockSettings

SECRET_PATTERN = r"(?i)(password|passwd|secret|api[_-]?key|token|authorization)\s*[:=]"
INJECTION_MARKERS = (
    "ignore as instruções",
    "ignore previous",
    "revelar credencial",
    "revele as credenciais",
    "system prompt",
    "publique a formulação",
    "aprove automaticamente",
)
UNSAFE_PRODUCTION = (
    "coma cru",
    "sem higienizar",
    "ignore a temperatura de segurança",
    "use produto químico não alimentar",
)
MEDICAL_CLAIMS = (
    "cura",
    "trata diabetes",
    "previne câncer",
    "uso medicinal",
    "recomendação médica",
)
ALLERGEN_ABSENCE = (
    "livre de glúten garantido",
    "sem alergênico garantido",
    "ausência total de alergênico",
    "100% livre de alergênico",
)
COMPLIANCE_CLAIMS = (
    "está em conformidade",
    "atende a anvisa",
    "rótulo aprovado",
    "declaração de conformidade",
)
APPROVAL_BYPASS = (
    "publique agora",
    "pular aprovação",
    "aprovar sem revisão",
    "publicar automaticamente",
)


class GuardrailError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def require_production_guardrail(settings: BedrockSettings | None, environ=None) -> None:
    env = (environ if environ is not None else os.environ).get("PANNE_ENV") or get_settings().env
    gateway = (environ if environ is not None else os.environ).get("PANNE_AI_GATEWAY", "")
    if env != "production":
        return
    if gateway == "fake":
        raise GuardrailError("guardrail_obrigatorio", "Ambiente de produção não aceita gateway falso.")
    if settings is None or not settings.guardrail_id:
        raise GuardrailError(
            "guardrail_obrigatorio",
            "O Guardrail da AWS é obrigatório em produção.",
        )


def scan_text(value: str, *, field: str = "entrada") -> list[dict]:
    alerts: list[dict] = []
    lowered = value.lower()
    if re.search(SECRET_PATTERN, value):
        raise GuardrailError("segredo_recusado", f"{field} não pode registrar segredo.")
    for marker in INJECTION_MARKERS:
        if marker in lowered:
            alerts.append({"code": "prompt_injection", "field": field})
    for marker in UNSAFE_PRODUCTION:
        if marker in lowered:
            raise GuardrailError(
                "instrucao_insegura",
                "Instrução insegura para produção de alimentos foi recusada.",
            )
    for marker in MEDICAL_CLAIMS:
        if marker in lowered:
            raise GuardrailError("alegacao_medica", "Alegação médica não é permitida.")
    for marker in ALLERGEN_ABSENCE:
        if marker in lowered:
            raise GuardrailError(
                "promessa_alergenico",
                "Não é permitido prometer ausência de alergênico.",
            )
    for marker in COMPLIANCE_CLAIMS:
        if marker in lowered:
            raise GuardrailError(
                "declaracao_conformidade",
                "A IA não declara conformidade.",
            )
    for marker in APPROVAL_BYPASS:
        if marker in lowered:
            raise GuardrailError(
                "burla_aprovacao",
                "Não é permitido burlar aprovação ou publicação.",
            )
    return alerts


def scan_payload(payload: dict) -> list[dict]:
    alerts: list[dict] = []
    for key, value in payload.items():
        if isinstance(value, str):
            alerts.extend(scan_text(value, field=key))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    alerts.extend(scan_text(item, field=key))
    return alerts


def map_gateway_failure(exc: Exception) -> tuple[str, str]:
    code = getattr(exc, "error_code", None) or str(exc)
    mapping = {
        "ThrottlingException": ("throttling", "O serviço de modelo está ocupado. Tente de novo."),
        "ModelTimeoutException": ("timeout", "A geração excedeu o tempo limite."),
        "ServiceUnavailableException": (
            "servico_modelo_indisponivel",
            "O serviço de modelo está indisponível.",
        ),
        "guardrail_obrigatorio": (
            "guardrail_obrigatorio",
            "O Guardrail da AWS é obrigatório em produção.",
        ),
        "sdk_ausente": ("servico_modelo_indisponivel", "O serviço de modelo está indisponível."),
    }
    if isinstance(exc, GatewayError) and code in mapping:
        return mapping[code]
    if code in mapping:
        return mapping[code]
    if "guardrail" in code.lower() or "blocked" in code.lower():
        return ("guardrail_bloqueio", "O Guardrail bloqueou a geração.")
    return ("modelo_indisponivel", "Não foi possível gerar a proposta agora.")
