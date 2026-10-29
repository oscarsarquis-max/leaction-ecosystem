from app.core.config import get_settings
from app.domain.accompaniments import public_catalog, public_vitrine_visible
from app.domain.marketplace_client import clear_marketplace_cache
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.db_fixtures import draft_order, priced_catalog


def test_cold_cache_hides_menu_without_preview(client: TestClient, monkeypatch) -> None:
    clear_marketplace_cache()
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    get_settings.cache_clear()
    assert client.get("/api/v1/operations").json()["accompaniments_visible"] is False
    get_settings.cache_clear()


def test_preview_shows_menu_without_hub_or_prior_fetch(client: TestClient, monkeypatch) -> None:
    clear_marketplace_cache()
    monkeypatch.setenv("LOJADEPAES_ENV", "local")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_ACCOMPANIMENTS_PREVIEW", "true")
    get_settings.cache_clear()
    ops = client.get("/api/v1/operations").json()
    assert ops["accompaniments_visible"] is True
    catalog = client.get("/api/v1/accompaniments").json()
    assert catalog["enabled"] is True
    assert catalog["source_status"] == "local_preview"
    assert catalog["preview"] is True
    assert catalog["items"][0]["demo"] is True
    assert catalog["items"][0]["outbound_href"] is None
    assert catalog["items"][0]["commercial_enabled"] is False
    assert catalog["attribution_ready"] is False
    get_settings.cache_clear()


def test_preview_does_not_run_in_production_env(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_ENV", "production")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_ACCOMPANIMENTS_PREVIEW", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.accompaniments_preview_eligible is False
    assert public_vitrine_visible(db, settings) is False
    catalog = public_catalog(db, settings)
    assert catalog["enabled"] is False
    get_settings.cache_clear()


def test_preview_hub_down_does_not_break_bread_order(client: TestClient, db: Session, monkeypatch) -> None:
    catalog = priced_catalog(db)
    monkeypatch.setenv("LOJADEPAES_ENV", "local")
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_ACCOMPANIMENTS_PREVIEW", "true")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_MARKETPLACE_URL", "http://127.0.0.1:9/api/marketplace")
    get_settings.cache_clear()

    def _boom(*_a, **_k):
        raise TimeoutError("hub down")

    monkeypatch.setattr("app.domain.marketplace_client.fetch_hub_profile_catalog", _boom)
    vitrine = client.get("/api/v1/accompaniments").json()
    assert vitrine["enabled"] is True
    assert vitrine["items"][0]["demo"] is True
    assert client.get("/api/v1/catalog/showcase").status_code == 200
    order = draft_order(db, catalog)
    assert order.public_reference.startswith("LP")
    get_settings.cache_clear()
