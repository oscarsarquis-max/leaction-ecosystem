"""Compat: reexporta o blueprint a partir de routes/daily_routes.py."""

from routes.daily_routes import daily_bp

__all__ = ["daily_bp"]
