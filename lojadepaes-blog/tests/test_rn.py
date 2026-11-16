import hashlib

from fastapi.testclient import TestClient

from app import cms, rn
from app.main import app


def test_cookie_and_hash_reach_the_hub(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_KEY", "segredo-teste")
    seen = {}

    def fake_lookup(slug):
        assert slug == "fornada-de-focaccia"
        return {"id": 41, "slug": slug, "secao": "right_now"}

    def fake_hub(method, path, body, ip):
        seen["method"] = method
        seen["path"] = path
        seen["body"] = body
        seen["ip"] = ip
        return 200, {"count": 3, "novo": True}

    monkeypatch.setattr(rn, "lookup", fake_lookup)
    monkeypatch.setattr(rn, "hub_request", fake_hub)
    pages = TestClient(app)
    first = pages.post("/api/rn/quero", json={"slug": "fornada-de-focaccia"})
    assert first.status_code == 200
    assert first.json() == {"count": 3, "voted": True}
    cookie = first.headers["set-cookie"]
    assert "lp_vid=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=31536000" in cookie
    vid = pages.cookies.get("lp_vid")
    expected = hashlib.sha256((vid + "segredo-teste").encode()).hexdigest()
    assert seen["body"]["visitante"] == expected
    assert seen["path"] == "/api/cms/posts/41/quero"

    def again(method, path, body, ip):
        seen["second"] = body["visitante"]
        return 200, {"count": 3, "novo": False}

    monkeypatch.setattr(rn, "hub_request", again)
    second = pages.post("/api/rn/quero", json={"slug": "fornada-de-focaccia"})
    assert second.status_code == 200
    assert second.json()["count"] == 3
    assert seen["second"] == expected


def test_enquete_maps_the_open_poll_and_null(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_KEY", "segredo-teste")

    def empty(method, path, body, ip):
        assert "visitante=" in path
        return 200, None

    monkeypatch.setattr(rn, "hub_request", empty)
    pages = TestClient(app)
    missing = pages.get("/api/rn/enquete?idioma=pt")
    assert missing.status_code == 200
    assert missing.json() is None
    assert "lp_vid=" in missing.headers["set-cookie"]

    def full(method, path, body, ip):
        return 200, {
            "id": 7,
            "pergunta_pt": "Qual pão?",
            "pergunta_en": "Which bread?",
            "opcoes": [{"id": "a", "pt": "Focaccia", "en": "Focaccia"}],
            "fecha_em": "2026-11-20T18:00:00.000Z",
            "votou": True,
            "resultado": [{"id": "a", "pct": 100}],
            "total": 4,
        }

    monkeypatch.setattr(rn, "hub_request", full)
    shown = pages.get("/api/rn/enquete?idioma=en")
    assert shown.status_code == 200
    body = shown.json()
    assert body["pergunta"] == "Which bread?"
    assert body["opcoes"] == [{"id": "a", "texto": "Focaccia"}]
    assert body["resultado"] == [{"id": "a", "pct": 100}]
    assert body["total"] == 4
    assert body["votou"] is True


def test_ics_is_a_calendar_only_for_events(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "fixtures")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    monkeypatch.setenv("LEPAIN_PUBLIC_URL", "https://lepain.lojadepaes.com.br")
    cms.reset_cache()
    pages = TestClient(app)
    calendar = pages.get("/pt/right-now/evento-da-semana.ics")
    assert calendar.status_code == 200
    assert calendar.headers["content-type"].startswith("text/calendar")
    text = calendar.text
    assert "BEGIN:VCALENDAR" in text
    assert "END:VCALENDAR" in text
    assert "DTSTART;VALUE=DATE:20261121" in text
    assert "SUMMARY:" in text
    assert "URL:https://lepain.lojadepaes.com.br/pt/right-now/evento-da-semana" in text
    assert pages.get("/pt/right-now/fornada-de-focaccia.ics").status_code == 404
