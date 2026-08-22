"""Limite ingredient_catalog — persistência e regras de invariante; sem API."""

from app.modules.ingredient_catalog import models as models
from app.modules.ingredient_catalog import rules as rules

__all__ = ["models", "rules"]
