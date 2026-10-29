from app.domain.actionhub_client import HubUnavailableError
from app.domain.baker_library.spider import invoke
from app.core.config import get_settings


def test_spider_invoke_does_not_call_hub(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOJADEPAES_SPIDER_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("LOJADEPAES_SPIDER_SATELLITE_SECRET", "test-satellite")
    get_settings.cache_clear()
    settings = get_settings()

    def boom(*_a, **_k):
        raise AssertionError("Loja não pode chamar o Hub neste fluxo")

    captured = {}

    class Response:
        status_code = 200
        content = b"{}"

        def json(self):
            return {
                "status": "READY",
                "capabilityId": "LIST_HUB_CATALOG",
                "resultSummary": {"app_id": "lojadepaes", "plans": []},
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["json"] = kwargs.get("json")
        assert "/hub-api" not in url
        assert "/v1/catalog" not in url
        return Response()

    monkeypatch.setattr("app.domain.baker_library.spider.httpx.post", fake_post)
    payload = invoke(
        settings,
        "LIST_HUB_CATALOG",
        {},
        correlation_id="loja-corr-catalog-test",
        idempotency_key="catalog:lojadepaes",
    )
    assert payload["app_id"] == "lojadepaes"
    assert captured["url"].endswith("/v1/satellites/interactions")
    assert captured["headers"]["X-Spider-Satellite-Id"] == "lojadepaes"
    assert captured["json"]["purpose"] == "LOJA_BIBLIOTECA"
    assert captured["json"]["objective"]["text"] == "LIST_LOJA_PLANS"


def test_spider_timeout_is_recoverable(monkeypatch) -> None:
    import httpx

    monkeypatch.setenv("LOJADEPAES_SPIDER_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("LOJADEPAES_SPIDER_SATELLITE_SECRET", "test-satellite")
    get_settings.cache_clear()

    def timeout(*_a, **_k):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr("app.domain.baker_library.spider.httpx.post", timeout)
    try:
        invoke(
            get_settings(),
            "LIST_HUB_CATALOG",
            {},
            correlation_id="loja-corr-timeout",
            idempotency_key="catalog:timeout",
        )
        raise AssertionError("deveria falhar de forma recuperável")
    except HubUnavailableError as exc:
        assert "timeout" in str(exc)
