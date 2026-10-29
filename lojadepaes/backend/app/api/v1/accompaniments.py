from fastapi import APIRouter, Response

from app.api.deps import AppSettings, DbSession
from app.domain.accompaniments import public_catalog, public_for_product

router = APIRouter(prefix="/accompaniments", tags=["accompaniments"])


@router.get("")
def get_accompaniments(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    cats: str = "",
    tipo: str = "",
    pao: str = "",
    ids: str = "",
    mesa: str = "",
    cerveja: str = "",
    forma: str = "",
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return public_catalog(
        db,
        settings,
        refresh=False,
        cats=cats,
        tipo=tipo,
        pao=pao,
        ids=ids,
        mesa=mesa,
        cerveja=cerveja,
        forma=forma,
    )


@router.get("/for-product/{slug}")
def get_product_accompaniments(slug: str, db: DbSession, settings: AppSettings, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return public_for_product(db, settings, slug)
