"""Modelos de domínio da Loja de Pães."""

from app.db.base import Base
from app.models.admin import (
    AdminAccount,
    AdminActivationDispatch,
    AdminActivationToken,
    AdminLoginAttempt,
    AdminSession,
)
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
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.email_outbox import EmailOutbox
from app.models.orders import (
    Order,
    OrderInternalNote,
    OrderItem,
    OrderItemAdaptation,
    OrderItemAdaptationEvent,
    OrderItemIngredient,
    OrderStatusHistory,
)
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from app.models.production import FulfillmentSlot, ProductionBatch, ProductionBatchDoughLimit
from app.models.products import (
    MediaAsset,
    Product,
    ProductEvent,
    ProductIngredient,
    ProductVariant,
    ShowcaseSlot,
)
from app.models.schedule import (
    RecipeBase,
    ScheduleDateOverride,
    ScheduleEligibleBase,
    ScheduleSettings,
    ScheduleWeekOverride,
)

__all__ = [
    "AdminAccount",
    "AdminActivationDispatch",
    "AdminActivationToken",
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
    "DateRequest",
    "DateRequestEvent",
    "EmailOutbox",
    "FulfillmentSlot",
    "Ingredient",
    "IngredientAllergen",
    "InspirationPost",
    "Order",
    "OrderInternalNote",
    "OrderItem",
    "OrderItemAdaptation",
    "OrderItemAdaptationEvent",
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
    "ShowcaseSlot",
    "RecipeBase",
    "ScheduleDateOverride",
    "ScheduleEligibleBase",
    "ScheduleSettings",
    "ScheduleWeekOverride",
]
