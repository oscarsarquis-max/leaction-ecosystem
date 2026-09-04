from fastapi import APIRouter, HTTPException, Request

from app.modules.demo_guide.service import resolve_demo_guide

router = APIRouter()


@router.get("/api/v1/public/demo-guide")
def get_demo_guide(request: Request) -> dict:
    """
    Guia operacional da demonstração.
    Somente PANNE_ENV=demo. Sem autenticação.
    Não aceita organization_id nem outros parâmetros do navegador.
    """
    _ = request
    payload = resolve_demo_guide()
    if payload is None:
        raise HTTPException(status_code=404, detail="nao_disponivel")
    return payload
