import logging

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AppSettings, DbSession, LojaSession
from app.api.v1 import auth, estoque, hoje, produtos, receitas, usuarios
from app.loja_reader.demanda import verificar_contrato

api_router = APIRouter()
log = logging.getLogger("gestao.ready")


@api_router.get("/health", tags=["saude"])
def health() -> dict[str, str]:
    """Vivo: o processo responde. Usado pelo healthcheck do contêiner."""
    return {"status": "ok"}


@api_router.get("/ready", tags=["saude"])
def ready(
    response: Response, db: DbSession, loja: LojaSession, settings: AppSettings
) -> dict[str, object]:
    """Pronto: banco do Gestão, sessão configurada e leitura da Loja compatível."""
    estado: dict[str, object] = {
        "gestao_db": False,
        "sessao": settings.session_ready,
        "loja_leitura": False,
    }
    try:
        db.execute(text("SELECT 1"))
        estado["gestao_db"] = True
    except SQLAlchemyError:
        log.exception("banco do Gestão indisponível")
    try:
        verificar_contrato(loja, fuso=settings.bakery_timezone)
        estado["loja_leitura"] = True
    except SQLAlchemyError:
        log.exception("leitura da Loja indisponível ou incompatível")
        loja.rollback()
    ok = all(estado.values())
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "indisponivel", **estado}


api_router.include_router(auth.router)
api_router.include_router(hoje.router)
api_router.include_router(estoque.router)
api_router.include_router(produtos.router)
api_router.include_router(receitas.router)
api_router.include_router(usuarios.router)
