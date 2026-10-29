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
    "published_frozen": "Versão publicada é imutável. Crie outra versão para editar.",
    "aprovacao_obrigatoria": "A publicação exige aprovação válida mais recente.",
    "composicao_ciclica": "A composição formaria um ciclo e foi rejeitada.",
    "grounding_insuficiente": "Não há evidência suficiente para gerar a proposta.",
    "guardrail_bloqueio": "O Guardrail bloqueou a geração.",
    "guardrail_obrigatorio": "O Guardrail da AWS é obrigatório neste ambiente.",
    "timeout": "A geração excedeu o tempo limite.",
    "throttling": "O serviço de modelo está ocupado. Tente de novo.",
    "servico_modelo_indisponivel": "O serviço de modelo está indisponível.",
    "modelo_indisponivel": "Não foi possível gerar a proposta agora.",
    "schema_invalido": "A proposta gerada não respeitou o contrato.",
    "citacao_invalida": "A citação não corresponde às evidências recuperadas.",
    "id_inventado": "A proposta usou um identificador não permitido.",
    "item_nao_resolvido": "Há componente sem resolução. A IA não cria ingrediente.",
    "proposta_invalida": "A proposta não pode seguir neste estado.",
    "proposta_ja_materializada": "Esta proposta já foi materializada em rascunho.",
    "confirmacao_obrigatoria": "Confirme o aceite em conjunto para continuar.",
    "concorrencia_excedida": "Há outras propostas em andamento. Aguarde.",
    "instrucao_insegura": "Instrução insegura para produção de alimentos foi recusada.",
    "alegacao_medica": "Alegação médica não é permitida.",
    "promessa_alergenico": "Não é permitido prometer ausência de alergênico.",
    "declaracao_conformidade": "A IA não declara conformidade.",
    "burla_aprovacao": "Não é permitido burlar aprovação ou publicação.",
    "segredo_recusado": "A entrada não pode registrar segredo.",
    "unidade_incompativel": "Unidade incompatível. Use apenas massa.",
    "moeda_incompativel": "Moeda incompatível. Não há conversão cambial nesta versão.",
    "dupla_contagem": "A origem já foi incluída neste cálculo.",
    "denominador_invalido": "Denominador inválido para a fórmula de preço.",
    "confirmacao_reforcada_obrigatoria": "Cálculo parcial exige confirmação reforçada e justificativa.",
    "periodo_excedido": "O período solicitado excede o limite síncrono de 90 dias.",
    "filtro_invalido": "Filtro inválido para este relatório.",
    "relatorio_desconhecido": "Relatório não autorizado ou inexistente.",
    "metrica_desconhecida": "Métrica não autorizada ou inexistente.",
    "snapshot_imutavel": "Snapshot emitido não é recalculado.",
    "exportacao_excedida": "A exportação excede o limite de linhas autorizado.",
    "conjunto_indisponivel": "O indicador está indisponível por ausência de denominador ou conjunto vazio.",
    "saldo_insuficiente": "Não há saldo disponível para esta saída ou reserva.",
    "lote_indisponivel": "O lote está vencido, bloqueado, em quarentena ou encerrado.",
    "lote_obrigatorio": "A política exige lote para este item.",
    "politica_nao_publicada": "Não há política de estoque publicada.",
    "compra_automatica_proibida": "A Panne não emite compra automática neste ciclo.",
    "preco_nao_atualizado": "O preço observado não atualiza o cadastro sem confirmação humana.",
    "inventario_fechado": "Inventário fechado é imutável. Abra um novo ciclo para corrigir.",
    "adocao_historica": "Ordem anterior ao estoque exige comando humano de adoção.",
    "codigo_duplicado": "Já existe um registro com este código nesta organização.",
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
        raise HTTPException(status_code=422, detail=public_error(code, _MESSAGES.get(code, reason)))
    raise HTTPException(status_code=400, detail=public_error("contrato_invalido"))


def sanitized_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content=public_error("contrato_invalido"))
