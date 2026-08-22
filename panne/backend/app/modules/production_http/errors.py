"""Erros HTTP estáveis. Sem SQL, token ou stack."""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.modules.identity_organization.authorization import AuthorizationError
from app.modules.identity_organization.services import IdentityResolutionError
from app.modules.production_planning.errors import (
    ConcurrencyError,
    CycleError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    PermissionDeniedError,
    ValidationError,
)

_MESSAGES = {
    "nao_autenticado": "Autenticação obrigatória.",
    "nao_autorizado": "Não autorizado.",
    "permissao_negada": "Não autorizado.",
    "organizacao_nao_selecionada": "Organização não selecionada.",
    "organizacao_divergente": "A organização da rota não corresponde à associação ativa.",
    "organizacao_invalida": "Organização inválida.",
    "escalada_indevida": "Não é permitido conceder ou revogar este papel.",
    "recurso_nao_encontrado": "Recurso não encontrado.",
    "contrato_invalido": "Contrato inválido.",
    "versao_conflito": "A versão do recurso mudou. Recarregue e tente de novo.",
    "idempotencia_conflito": "A chave de idempotência já foi usada com outro comando.",
    "idempotencia_obrigatoria": "Informe Idempotency-Key.",
    "correlacao_obrigatoria": "Informe X-Correlation-Id.",
    "etag_obrigatorio": "Informe If-Match com a versão do recurso.",
    "indisponivel": "Dependência indisponível.",
    "transicao_invalida": "A transição não é permitida no estado atual.",
    "politica_ja_adotada": "A ordem já possui política congelada.",
    "adocao_bloqueada_por_fatos": "Não é possível adotar política após fatos de execução.",
    "ultimo_proprietario": "Não é possível revogar o último proprietário ativo.",
    "ultimo_papel_ativo": "A associação precisa manter ao menos um papel ativo.",
    "conversao_massa_volume_proibida": "Conversão entre massa e volume não é permitida.",
}


def public_error(code: str, message: str | None = None) -> dict[str, str]:
    return {"code": code, "message": message or _MESSAGES.get(code, "Solicitação recusada.")}


def _hidden_resource(reason: str) -> bool:
    lowered = reason.lower()
    return "inválid" in lowered or "inexistente" in lowered or "nao_encontrado" in lowered


def raise_domain(exc: Exception) -> None:
    if isinstance(exc, (AuthorizationError, PermissionDeniedError, IdentityResolutionError)):
        code = getattr(exc, "reason", "nao_autorizado")
        raise HTTPException(status_code=403, detail=public_error(code, _MESSAGES.get(code)))
    if isinstance(exc, ConcurrencyError):
        raise HTTPException(status_code=409, detail=public_error("versao_conflito"))
    if isinstance(exc, IdempotencyConflictError):
        raise HTTPException(status_code=409, detail=public_error("idempotencia_conflito"))
    if isinstance(exc, (InvalidStateError, ImmutableError, CycleError)):
        code = getattr(exc, "reason", "transicao_invalida")
        raise HTTPException(
            status_code=409, detail=public_error(code, _MESSAGES.get(code, str(exc)))
        )
    if isinstance(exc, ValidationError):
        reason = str(exc)
        if _hidden_resource(reason):
            raise HTTPException(status_code=404, detail=public_error("recurso_nao_encontrado"))
        code = reason if reason in _MESSAGES else "regra_de_dominio"
        raise HTTPException(
            status_code=422, detail=public_error(code, _MESSAGES.get(code, reason))
        )
    raise HTTPException(status_code=400, detail=public_error("contrato_invalido"))


def sanitized_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content=public_error("contrato_invalido"))
