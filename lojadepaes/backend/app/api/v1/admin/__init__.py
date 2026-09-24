from fastapi import APIRouter

from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.date_requests import router as date_requests_router
from app.api.v1.admin.orders import router as orders_router
from app.api.v1.admin.products import media_router
from app.api.v1.admin.products import router as products_router
from app.api.v1.admin.schedule import router as schedule_router
from app.api.v1.admin.showcase import router as showcase_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(orders_router)
router.include_router(products_router)
router.include_router(media_router)
router.include_router(schedule_router)
router.include_router(showcase_router)
router.include_router(date_requests_router)
