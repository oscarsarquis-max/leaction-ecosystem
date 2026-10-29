"""R028-002 — guia público da demo (somente PANNE_ENV=demo)."""

from __future__ import annotations

import json
import os
import re
from unittest.mock import patch

from app.config import get_settings
from app.main import app
from app.modules.demo_guide.content import FALLBACK_COUNTS, static_guide_body
from app.modules.demo_guide.service import resolve_demo_guide
from fastapi.testclient import TestClient

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
SECRETISH = re.compile(r"(password|secret|token|arn:aws|connection.?string)", re.I)


def _with_env(value: str):
    return patch.dict(os.environ, {"PANNE_ENV": value}, clear=False)


def test_demo_guide_404_outside_demo() -> None:
    get_settings.cache_clear()
    with _with_env("production"):
        get_settings.cache_clear()
        assert resolve_demo_guide() is None
        client = TestClient(app)
        assert client.get("/api/v1/public/demo-guide").status_code == 404
    get_settings.cache_clear()


def test_demo_guide_available_in_demo_without_auth() -> None:
    get_settings.cache_clear()
    with _with_env("demo"):
        get_settings.cache_clear()
        with patch("app.modules.demo_guide.service.RuntimeSessionLocal", None):
            client = TestClient(app)
            response = client.get(
                "/api/v1/public/demo-guide",
                params={"organization_id": "evil", "token": "x"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["schema_version"] == 1
            assert body["content_version"] == "r028-004-economy"
            assert len(body["profiles"]) == 7
            assert len(body["roadmap"]) == 14
            assert body["source"] in {"live", "fallback"}
            assert body["counts"]["totals"]["perfis_disponiveis"] == 7
            blob = json.dumps(body, ensure_ascii=False)
            assert not UUID_RE.search(blob)
            assert not EMAIL_RE.search(blob)
            assert not SECRETISH.search(blob)
            assert "organization_id" not in blob.lower() or "organization_id" not in str(
                body.get("counts")
            )
    get_settings.cache_clear()


def test_fallback_counts_never_invent_missing_as_zero_sentinel() -> None:
    assert FALLBACK_COUNTS["organizations"][1]["counts"]["perfis_disponiveis"] is None
    body = static_guide_body()
    assert body["limitations"]
    assert any("separação" in item.lower() or "separacao" in item.lower() for item in body["limitations"])
    assert all("detail" in row for row in body["integrations"])
