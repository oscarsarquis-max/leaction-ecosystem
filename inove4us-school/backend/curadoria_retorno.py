"""Retorno ao docente + texto do aviso de curadoria (unidirecional)."""

from __future__ import annotations

from typing import Any

TIPO_RESPOSTA = "resposta_proposta_metodologica"
ROTULO_RESPOSTA = "[Resposta à Proposta Metodológica]"
RETORNO_MAX = 2000

RESULTADO_LABEL = {
    "aprovada": "Aprovada",
    "adaptada": "Adaptada",
    "nao_incorporada": "Não incorporada agora",
}


def ler_retorno_docente(body: Any) -> tuple[str | None, str | None]:
    """Retorna (texto, erro). Erro é mensagem clara para o coordenador."""
    data = body if isinstance(body, dict) else {}
    texto = str(
        data.get("retorno_docente") or data.get("retorno") or ""
    ).strip()
    if not texto:
        return None, "Informe o retorno ao docente antes de resolver a sugestão."
    if len(texto) > RETORNO_MAX:
        return None, f"O retorno ao docente deve ter no máximo {RETORNO_MAX} caracteres."
    return texto, None


def resumo_sugestao(texto: str, limit: int = 280) -> str:
    compact = " ".join(str(texto or "").split())
    if not compact:
        return "(sem texto da proposta)"
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"


def montar_texto_aviso(
    *,
    resultado: str,
    sugestao_original: str,
    retorno: str,
) -> str:
    label = RESULTADO_LABEL.get(resultado, resultado)
    proposta = resumo_sugestao(sugestao_original)
    partes = [
        ROTULO_RESPOSTA,
        f"Resultado: {label}.",
        f"Sua proposta: {proposta}",
        f"Retorno da coordenação: {retorno.strip()}",
    ]
    return "\n\n".join(partes)[:4000]


def aviso_visivel_para_professor(
    *,
    aviso_professor_b2c_id: Any,
    id_clie: int,
) -> bool:
    """Aviso geral (sem alvo) ou aviso do próprio professor."""
    if aviso_professor_b2c_id in (None, ""):
        return True
    try:
        return int(aviso_professor_b2c_id) == int(id_clie)
    except (TypeError, ValueError):
        return False
