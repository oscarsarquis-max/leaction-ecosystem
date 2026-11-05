import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.domain.errors import ErroDeDominio

CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def _spa_dir(configured: str) -> Path | None:
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    for path in candidates:
        if path.is_dir() and (path / "index.html").is_file():
            return path
    return None


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    application = FastAPI(
        title="Loja de Pães – Gestão",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.middleware("http")
    async def cabecalhos_de_seguranca(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        response.headers.setdefault("Content-Security-Policy", CSP)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @application.exception_handler(ErroDeDominio)
    async def regra_violada(_request: Request, exc: ErroDeDominio) -> JSONResponse:
        return JSONResponse({"detail": exc.detalhe()}, status_code=exc.status)

    @application.exception_handler(Exception)
    async def erro_inesperado(_request: Request, _exc: Exception) -> JSONResponse:
        logging.getLogger("gestao").exception("erro inesperado")
        return JSONResponse({"detail": "erro interno"}, status_code=500)

    application.include_router(api_router, prefix="/api/v1")

    spa = _spa_dir(settings.spa_dir)
    if spa is not None:
        assets = spa / "assets"
        if assets.is_dir():
            application.mount("/assets", StaticFiles(directory=assets), name="spa-assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "não encontrado"}, status_code=404)
            candidate = (spa / full_path).resolve()
            if full_path and candidate.is_file() and spa in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(spa / "index.html", headers={"Cache-Control": "no-store"})

    return application


app = create_app()
