"""Validação de payloads de telemetria eSIM (sem catálogo — resolvido no webhook)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class EsimPayloadError(ValueError):
    pass


ESIM_CLASSIFICACAO_CLASSIFICADO = "classificado"
ESIM_CLASSIFICACAO_NAO_CLASSIFICADO = "nao_classificado"


@dataclass(frozen=True)
class EsimTelemetryPayload:
    cliente_id: int
    codigo_evento: str
    grupo_acesso: str
    dominio_acessado: str
    titulo_alerta: str
    descricao_evento: str
    status_anomalia: str
    trafego_mb_7dias: float | None
    variacao_percentual: float | None
    iccid: str | None
    timestamp_evento: str | None
    raw: dict[str, Any]

    @property
    def codigo_evento_padrao(self) -> str:
        """Alias legado usado por módulos de IA e Mesa."""
        return self.codigo_evento

    @property
    def is_queda_critica(self) -> bool:
        return self.status_anomalia.strip().lower() == "queda_critica"


def _esim_coalesce_titulo(data: dict[str, Any], status_anomalia: str, dominio: str) -> str:
    titulo = (data.get("titulo_alerta") or "").strip()
    if titulo:
        return titulo
    if status_anomalia and dominio:
        return f"{status_anomalia.replace('_', ' ').title()} — {dominio}"
    return "Alerta de telemetria eSIM"


def _esim_coalesce_descricao(data: dict[str, Any], grupo: str, dominio: str) -> str:
    descricao = (data.get("descricao_evento") or "").strip()
    if descricao:
        return descricao
    trafego = data.get("trafego_mb_7dias")
    variacao = data.get("variacao_percentual")
    partes = []
    if grupo:
        partes.append(f"Grupo de acesso: {grupo}.")
    if dominio:
        partes.append(f"Domínio afetado: {dominio}.")
    if trafego is not None:
        partes.append(f"Tráfego 7 dias: {trafego} MB.")
    if variacao is not None:
        partes.append(f"Variação percentual: {variacao}%.")
    return " ".join(partes) or "Evento de telemetria registrado pela operadora eSIM."


def _esim_parse_optional_float(data: dict[str, Any], field: str) -> float | None:
    raw = data.get(field)
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise EsimPayloadError(f"{field} deve ser numérico.") from exc


def _esim_rejeitar_campos_framework_externos(data: dict[str, Any]) -> None:
    proibidos = (
        "dimensao_fixada",
        "dominio_fixado",
        "blocos_candidatos_restritos",
        "blocos_candidatos",
        "bloco_associado",
        "dominio_associado",
        "interpretacao_leaction",
    )
    for key in proibidos:
        valor = data.get(key)
        if valor is not None and valor != "" and valor != []:
            raise EsimPayloadError(
                f"Campo '{key}' não é aceito no webhook da operadora; "
                "a correlação com o Framework LeAction é interna ao PanelDX."
            )


def _esim_resolver_codigo_evento(data: dict[str, Any]) -> str:
    codigo = (data.get("codigo_evento") or data.get("codigo_evento_padrao") or "").strip().upper()
    if not codigo:
        raise EsimPayloadError("Campo obrigatório: codigo_evento")
    return codigo


def esim_parse_telemetry_payload(data: dict[str, Any] | None) -> EsimTelemetryPayload:
    """Valida apenas campos de telecom; catálogo é resolvido no processador/webhook."""
    if not data or not isinstance(data, dict):
        raise EsimPayloadError("Corpo JSON inválido ou ausente.")

    _esim_rejeitar_campos_framework_externos(data)

    cliente_id = data.get("cliente_id")
    codigo_evento = _esim_resolver_codigo_evento(data)
    grupo_acesso = (data.get("grupo_acesso") or "").strip()
    dominio_acessado = (data.get("dominio_acessado") or "").strip()
    status_anomalia = (data.get("status_anomalia") or "").strip().lower()
    iccid = (data.get("iccid") or "").strip() or None
    timestamp_evento = (data.get("timestamp") or data.get("timestamp_evento") or "").strip() or None

    if cliente_id is None:
        raise EsimPayloadError("Campo obrigatório: cliente_id")
    try:
        cliente_id = int(cliente_id)
    except (TypeError, ValueError) as exc:
        raise EsimPayloadError("cliente_id deve ser numérico.") from exc

    if not grupo_acesso:
        raise EsimPayloadError("Campo obrigatório: grupo_acesso")
    if not dominio_acessado:
        raise EsimPayloadError("Campo obrigatório: dominio_acessado")
    if status_anomalia == "":
        raise EsimPayloadError("Campo obrigatório: status_anomalia")

    return EsimTelemetryPayload(
        cliente_id=cliente_id,
        codigo_evento=codigo_evento,
        grupo_acesso=grupo_acesso,
        dominio_acessado=dominio_acessado,
        titulo_alerta=_esim_coalesce_titulo(data, status_anomalia, dominio_acessado),
        descricao_evento=_esim_coalesce_descricao(data, grupo_acesso, dominio_acessado),
        status_anomalia=status_anomalia,
        trafego_mb_7dias=_esim_parse_optional_float(data, "trafego_mb_7dias"),
        variacao_percentual=_esim_parse_optional_float(data, "variacao_percentual"),
        iccid=iccid,
        timestamp_evento=timestamp_evento,
        raw=data,
    )


# Aliases legados
BaseMobilePayloadError = EsimPayloadError
BaseMobileTelemetryPayload = EsimTelemetryPayload
parse_basemobile_payload = esim_parse_telemetry_payload
