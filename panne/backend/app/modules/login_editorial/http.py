from fastapi import APIRouter, Request

from app.modules.login_editorial.service import resolve_editorial_payload

router = APIRouter()


@router.get("/api/v1/public/login-editorial")
def get_login_editorial(request: Request) -> dict:
    """
    Conteúdo editorial das colunas de /entrar.
    Sem autenticação.
    Não aceita config_key, mode nem outros parâmetros do navegador —
    query strings desconhecidas são ignoradas e não alteram a resposta.
    """
    # Explicitamente não lê request.query_params para comportamento editorial.
    _ = request  # Request disponível para auditoria futura; query ignorada.
    return resolve_editorial_payload()
