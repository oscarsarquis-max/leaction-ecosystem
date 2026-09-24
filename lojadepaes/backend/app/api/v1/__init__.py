from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.health import router as health_router
from app.api.v1.operations import router as operations_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.storefront import router as storefront_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(operations_router)
api_router.include_router(admin_router)
api_router.include_router(catalog_router)
api_router.include_router(schedule_router)
api_router.include_router(storefront_router)
