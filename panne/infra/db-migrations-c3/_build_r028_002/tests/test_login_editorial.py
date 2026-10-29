"""Testes de segurança editorial CURSOR-028-CMS (gate pontual)."""

from __future__ import annotations

import time
from unittest.mock import patch

from app.main import app
from app.modules.login_editorial.cache import cache_clear, cache_get, cache_get_stale, cache_set
from app.modules.login_editorial.config_key import resolve_login_editorial_config_key
from app.modules.login_editorial.content import sanitize_column, static_payload
from app.modules.login_editorial.mapper import map_hub_landing_to_panne
from app.modules.login_editorial.service import resolve_editorial_payload
from app.modules.login_editorial.url_policy import (
    DEFAULT_CTA_HOSTS,
    DEFAULT_MEDIA_HOSTS,
    sanitize_cta_url,
    sanitize_image_url,
)
from fastapi.testclient import TestClient

MEDIA = frozenset({"cdn.example.com", "paneldx-cms-assets-2026.s3.amazonaws.com"})
CTA = frozenset({"docs.leaction.com.br", "leaction.com.br"})


def setup_function() -> None:
    cache_clear()


def test_mode_query_does_not_alter_public_response() -> None:
    client = TestClient(app)
    with patch("app.modules.login_editorial.service.fetch_hub_cms", return_value=None):
        base = client.get("/api/v1/public/login-editorial").json()
        with_mode = client.get("/api/v1/public/login-editorial", params={"mode": "invalid"}).json()
        with_unavail = client.get(
            "/api/v1/public/login-editorial", params={"mode": "unavailable"}
        ).json()
        with_noise = client.get(
            "/api/v1/public/login-editorial", params={"foo": "bar", "config_key": "evil"}
        ).json()
    assert base["schema_version"] == 1
    assert with_mode["schema_version"] == 1
    assert with_mode.get("source") != "fallback" or with_mode["columns"]  # not forced invalid
    assert with_mode["schema_version"] != 99
    assert with_unavail["columns"]  # not empty forced unavailable
    assert with_noise["source"] == base["source"]
    assert {c["placement"] for c in with_noise["columns"]} == {"left", "right"}


def test_service_force_mode_still_works_in_tests_only() -> None:
    assert resolve_editorial_payload(force_mode="unavailable")["source"] == "fallback"
    assert resolve_editorial_payload(force_mode="invalid")["schema_version"] == 99


def test_image_https_unauthorized_host_rejected() -> None:
    assert sanitize_image_url("https://evil.example/x.png", media_hosts=MEDIA) == ""
    assert (
        sanitize_image_url(
            "https://paneldx-cms-assets-2026.s3.amazonaws.com/a.png", media_hosts=MEDIA
        )
        == "https://paneldx-cms-assets-2026.s3.amazonaws.com/a.png"
    )
    assert sanitize_image_url("/images/aprovados/x.png", media_hosts=MEDIA) == "/images/aprovados/x.png"


def test_cta_https_unauthorized_and_auth_paths() -> None:
    assert sanitize_cta_url("https://evil.example/x", cta_hosts=CTA) == ""
    assert (
        sanitize_cta_url("https://docs.leaction.com.br/guide", cta_hosts=CTA)
        == "https://docs.leaction.com.br/guide"
    )
    assert sanitize_cta_url("/docs/manual", cta_hosts=CTA) == "/docs/manual"
    assert sanitize_cta_url("/entrar", cta_hosts=CTA) == ""
    assert sanitize_cta_url("/callback", cta_hosts=CTA) == ""
    assert sanitize_cta_url("/logout", cta_hosts=CTA) == ""
    assert sanitize_cta_url("/auth/oidc", cta_hosts=CTA) == ""


def test_dangerous_schemes_and_credentials() -> None:
    for raw in (
        "ftp://x/a",
        "file:///etc/passwd",
        "data:text/html,hi",
        "javascript:alert(1)",
        "https://user:pass@cdn.example.com/a.png",
        "//cdn.example.com/a.png",
        "http://cdn.example.com/a.png",
    ):
        assert sanitize_image_url(raw, media_hosts=MEDIA) == ""
        assert sanitize_cta_url(raw, cta_hosts=CTA) == ""


def test_column_drops_bad_media_keeps_login_fields() -> None:
    col = sanitize_column(
        {
            "placement": "left",
            "title": "Ok",
            "image": {"url": "https://evil.example/a.png", "alt": "x"},
            "cta": {"label": "Go", "url": "ftp://x"},
        },
        media_hosts=MEDIA,
        cta_hosts=CTA,
    )
    assert col is not None
    assert col["title"] == "Ok"
    assert col["image"]["url"] == ""
    assert "cta" not in col


def test_config_key_prod_blocks_panne_demo_override() -> None:
    assert resolve_login_editorial_config_key(env="production", override="panne-demo") == "panne"
    assert resolve_login_editorial_config_key(env="prod", override="panne-demo") == "panne"
    assert (
        resolve_login_editorial_config_key(
            env="production",
            override="panne-demo",
            allow_demo_override_in_prod=True,
        )
        == "panne-demo"
    )
    assert resolve_login_editorial_config_key(env="demo") == "panne-demo"
    assert resolve_login_editorial_config_key(env="local", override="panne") == "panne"


def test_cache_fresh_stale_expired() -> None:
    cache_set("k", {"schema_version": 1, "source": "hub", "columns": [{"a": 1}]})
    assert cache_get("k", ttl_seconds=60) is not None
    # força idade antiga
    cache_set(
        "k",
        {"schema_version": 1, "source": "hub", "columns": [{"a": 1}]},
        fetched_at=time.time() - 120,
    )
    assert cache_get("k", ttl_seconds=30) is None
    assert cache_get_stale("k", max_stale_seconds=600) is not None
    assert cache_get_stale("k", max_stale_seconds=60) is None


def test_stale_expired_falls_to_static() -> None:
    cache_set(
        "login-editorial:panne-demo",
        {
            "schema_version": 1,
            "source": "hub",
            "columns": static_payload(media_hosts=MEDIA, cta_hosts=CTA)["columns"],
        },
        fetched_at=time.time() - 9999,
    )
    with patch("app.modules.login_editorial.service.fetch_hub_cms", return_value=None):
        with patch("app.modules.login_editorial.service.cache_get", return_value=None):
            body = resolve_editorial_payload()
    assert body["source"] == "static"


def test_stale_within_max_used() -> None:
    cols = static_payload(media_hosts=MEDIA, cta_hosts=CTA)["columns"]
    cache_set(
        "login-editorial:panne-demo",
        {"schema_version": 1, "source": "hub", "columns": cols, "note": "prev"},
        fetched_at=time.time() - 120,
    )
    with patch("app.modules.login_editorial.service.fetch_hub_cms", return_value=None):
        with patch("app.modules.login_editorial.service.cache_get", return_value=None):
            body = resolve_editorial_payload()
    assert body["source"] == "cache"
    assert body["columns"]


def test_mapper_authorized_media() -> None:
    static = static_payload(media_hosts=MEDIA, cta_hosts=CTA)["columns"]
    landing = {
        "coluna1": {
            "visibility": True,
            "title": "L",
            "subtitle": "S",
            "image_url": "https://cdn.example.com/a.png",
        },
        "columns": [
            {"title": "L", "description": "S", "visible": True},
            {
                "title": "R",
                "description": "S",
                "visible": True,
                "link_text": "Docs",
                "link_url": "https://docs.leaction.com.br/x",
            },
        ],
    }
    mapped = map_hub_landing_to_panne(
        landing, static_columns=static, media_hosts=MEDIA, cta_hosts=CTA
    )
    assert mapped is not None
    by = {c["placement"]: c for c in mapped["columns"]}
    assert by["left"]["image"]["url"].startswith("https://cdn.example.com/")
    assert by["right"]["cta"]["url"].startswith("https://docs.leaction.com.br/")


def test_public_no_auth() -> None:
    client = TestClient(app)
    with patch("app.modules.login_editorial.service.fetch_hub_cms", return_value=None):
        r = client.get("/api/v1/public/login-editorial")
    assert r.status_code == 200
    assert "ACTION_HUB" not in r.text


def test_defaults_media_hosts_documented() -> None:
    assert "paneldx-cms-assets-2026.s3.amazonaws.com" in DEFAULT_MEDIA_HOSTS
    assert "leaction.com.br" in DEFAULT_CTA_HOSTS
