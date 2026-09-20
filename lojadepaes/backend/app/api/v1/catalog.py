from uuid import UUID

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

from app.api.deps import AppSettings, DbSession
from app.domain.media import media_file
from app.domain.products import public_detail, public_list, published_media
from app.schemas.catalog_public import PublicProductDetail, PublicProductList

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/products", response_model=PublicProductList)
def catalog_list(
    db: DbSession,
    response: Response,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> PublicProductList:
    response.headers["Cache-Control"] = "no-store"
    return public_list(db, page, page_size)


@router.get("/products/{slug}", response_model=PublicProductDetail)
def catalog_detail(slug: str, db: DbSession, response: Response) -> PublicProductDetail:
    response.headers["Cache-Control"] = "no-store"
    return public_detail(db, slug)


@router.get("/media/{media_id}")
def catalog_media(media_id: UUID, db: DbSession, settings: AppSettings) -> Response:
    asset = published_media(db, media_id)
    path = media_file(settings, asset.stored_name)
    return FileResponse(
        path,
        media_type=asset.content_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=86400, immutable",
        },
    )
