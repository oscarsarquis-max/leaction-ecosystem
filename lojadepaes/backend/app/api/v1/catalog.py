from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response

from app.api.deps import AppSettings, DbSession, PreviewGate
from app.domain.media import open_media
from app.domain.products import public_detail, public_list, published_media
from app.domain.showcase import public_showcase
from app.schemas.catalog_public import PublicProductDetail, PublicProductList

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/showcase", response_model=PublicProductList)
def catalog_showcase(db: DbSession, response: Response, _: PreviewGate) -> PublicProductList:
    response.headers["Cache-Control"] = "no-store"
    return public_showcase(db)


@router.get("/products", response_model=PublicProductList)
def catalog_list(
    db: DbSession,
    response: Response,
    _: PreviewGate,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> PublicProductList:
    response.headers["Cache-Control"] = "no-store"
    return public_list(db, page, page_size)


@router.get("/products/{slug}", response_model=PublicProductDetail)
def catalog_detail(
    slug: str, db: DbSession, response: Response, _: PreviewGate
) -> PublicProductDetail:
    response.headers["Cache-Control"] = "no-store"
    return public_detail(db, slug)


@router.get("/media/{media_id}")
def catalog_media(
    media_id: UUID, db: DbSession, settings: AppSettings, _: PreviewGate
) -> Response:
    asset = published_media(db, media_id)
    opened = open_media(settings, asset.object_key or asset.stored_name, asset.storage_backend)
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "public, max-age=86400, immutable",
    }
    if hasattr(opened, "read_bytes"):
        return FileResponse(opened, media_type=asset.content_type, headers=headers)
    return Response(content=opened, media_type=asset.content_type, headers=headers)
