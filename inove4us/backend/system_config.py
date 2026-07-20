"""Estado global do gatekeeper (system_locked) — espelha mudaedu/PanelDX."""

from __future__ import annotations

import os
import time

from db import get_conn

CACHE_TTL_MS = int(os.environ.get("SYSTEM_CONFIG_CACHE_MS", "15000"))

_locked_cache: dict = {"value": None, "expires_at": 0.0}
_table_ready = False


def invalidate_system_config_cache() -> None:
    _locked_cache["value"] = None
    _locked_cache["expires_at"] = 0.0


def set_system_locked_cache(locked: bool) -> None:
    _locked_cache["value"] = bool(locked)
    _locked_cache["expires_at"] = time.time() + (CACHE_TTL_MS / 1000.0)


def ensure_system_config_table() -> None:
    global _table_ready
    if _table_ready:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.system_config (
                    config_key   TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                INSERT INTO public.system_config (config_key, config_value)
                VALUES ('system_locked', 'true')
                ON CONFLICT (config_key) DO NOTHING
                """
            )
    _table_ready = True


def is_system_locked() -> bool:
    now = time.time()
    if _locked_cache["value"] is not None and now < _locked_cache["expires_at"]:
        return bool(_locked_cache["value"])

    ensure_system_config_table()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT config_value FROM public.system_config
                WHERE config_key = 'system_locked' LIMIT 1
                """
            )
            row = cur.fetchone()
    locked = True if not row else str(row[0]).strip().lower() == "true"
    set_system_locked_cache(locked)
    return locked


def unlock_system() -> None:
    ensure_system_config_table()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.system_config (config_key, config_value, updated_at)
                VALUES ('system_locked', 'false', CURRENT_TIMESTAMP)
                ON CONFLICT (config_key) DO UPDATE
                SET config_value = EXCLUDED.config_value,
                    updated_at = CURRENT_TIMESTAMP
                """
            )
    set_system_locked_cache(False)


def lock_system() -> None:
    ensure_system_config_table()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.system_config (config_key, config_value, updated_at)
                VALUES ('system_locked', 'true', CURRENT_TIMESTAMP)
                ON CONFLICT (config_key) DO UPDATE
                SET config_value = EXCLUDED.config_value,
                    updated_at = CURRENT_TIMESTAMP
                """
            )
    set_system_locked_cache(True)
