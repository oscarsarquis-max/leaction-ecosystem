"""Modelos de domínio da Loja de Pães."""

from app.db.base import Base
from app.models.admin import AdminLoginAttempt, AdminSession
from app.models.catalog import (
    Allergen,
    BreadShape,
    DoughAllergen,
    DoughIngredientCompatibility,
    DoughShapeCompatibility,
    DoughType,
    Ingredient,
    IngredientAllergen,
    PairingTip,
)
from app.models.content import Article, InspirationPost
from app.models.orders import (
    Order,
    OrderInternalNote,
    OrderItem,
    OrderItemIngredient,
    OrderStatusHistory,
)
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from app.models.production import FulfillmentSlot, ProductionBatch, ProductionBatchDoughLimit
from app.models.products import MediaAsset, Product, ProductEvent, ProductIngredient, ProductVariant

__all__ = [
    "AdminLoginAttempt",
    "AdminSession",
    "Allergen",
    "Article",
    "Base",
    "BreadShape",
    "DoughAllergen",
    "DoughIngredientCompatibility",
    "DoughShapeCompatibility",
    "DoughType",
    "FulfillmentSlot",
    "Ingredient",
    "IngredientAllergen",
    "InspirationPost",
    "Order",
    "OrderInternalNote",
    "OrderItem",
    "OrderItemIngredient",
    "OrderStatusHistory",
    "PairingTip",
    "PaymentIntegrationEvent",
    "PaymentRecord",
    "ProductionBatch",
    "ProductionBatchDoughLimit",
    "MediaAsset",
    "Product",
    "ProductEvent",
    "ProductIngredient",
    "ProductVariant",
]
