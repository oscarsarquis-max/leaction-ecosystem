from fastapi.testclient import TestClient

from app import cms
from app.main import app
from app.sanitize import clean


def client(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "fixtures")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    cms.reset_cache()
    return TestClient(app)


def test_pt_and_en_hreflang(monkeypatch):
    pages = client(monkeypatch)
    assert pages.get("/pt").status_code == 200
    assert pages.get("/en").status_code == 200
    pt = pages.get("/pt/insights/a-casca-que-canta")
    en = pages.get("/en/insights/the-crust-that-sings")
    assert pt.status_code == 200
    assert en.status_code == 200
    assert 'hreflang="en"' in pt.text
    assert "/en/insights/the-crust-that-sings" in pt.text
    assert 'hreflang="pt"' in en.text
    assert "/pt/insights/a-casca-que-canta" in en.text
    assert 'rel="canonical"' in pt.text
    assert "/pt/insights/a-casca-que-canta" in pt.text
    assert 'property="og:locale" content="pt_BR"' in pt.text
    assert 'property="og:image"' in pt.text
    assert "English version coming soon" not in en.text


def test_pt_only_shows_english_notice(monkeypatch):
    pages = client(monkeypatch)
    page = pages.get("/en/insights/o-silencio-da-massa-descansando")
    assert page.status_code == 200
    assert "English version coming soon" in page.text
    assert "O silêncio da massa descansando" in page.text


def test_hub_discards_todos(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "hub")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    cms.reset_cache()

    def fake_payload():
        return [
            {
                "sistema_destino": "todos",
                "status": "publicado",
                "slug": "vazou",
                "titulo": "Nao pode aparecer",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "x",
                "conteudo_html": "<p>x</p>",
                "grupo_id": 1,
                "publicado_em": "2026-11-02",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "fica",
                "titulo": "Fica no blog",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "y",
                "conteudo_html": "<p>y</p>",
                "grupo_id": 2,
                "sentidos": ["som"],
                "publicado_em": "2026-11-01",
            },
        ]

    monkeypatch.setattr(cms, "fetch_hub_payload", fake_payload)
    page = TestClient(app).get("/pt")
    assert page.status_code == 200
    assert "Nao pode aparecer" not in page.text
    assert "Fica no blog" in page.text


def test_sanitize_strips_script_and_foreign_iframe():
    raw = (
        "<p>ok</p><script>alert(1)</script>"
        '<iframe src="https://evil.test/x"></iframe>'
        '<iframe src="https://www.youtube.com/embed/abc" title="v"></iframe>'
        '<iframe src="https://player.vimeo.com/video/1" title="v"></iframe>'
    )
    out = clean(raw)
    assert "<script" not in out.lower()
    assert "alert" not in out
    assert "evil.test" not in out
    assert "youtube.com/embed/abc" in out
    assert "player.vimeo.com/video/1" in out


def test_right_now_hides_expired(monkeypatch):
    pages = client(monkeypatch)
    page = pages.get("/pt/right-now")
    assert page.status_code == 200
    assert "Fornada encerrada" not in page.text
    assert "Fornada de Focaccia" in page.text
    english = pages.get("/en/right-now")
    assert "Bake that ended" not in english.text
    assert "Focaccia bake" in english.text


def test_hub_list_url_filters_and_slug(monkeypatch):
    monkeypatch.setenv("LEPAIN_HUB_URL", "https://api.actionhub.com.br")
    url = cms.list_url(secao="insights", idioma="en", offset=40)
    assert url.startswith("https://api.actionhub.com.br/api/cms/posts?")
    assert "sistema_destino=lepain" in url
    assert "secao=insights" in url
    assert "idioma=en" in url
    assert "offset=40" in url
    assert cms.post_url("a-casca") == "https://api.actionhub.com.br/api/cms/posts/a-casca"


def test_hub_sibling_by_grupo_and_discards_todos(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "hub")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    cms.reset_cache()

    def fake_payload(secao="", idioma=""):
        return [
            {
                "sistema_destino": "todos",
                "status": "publicado",
                "slug": "vazou",
                "titulo": "Nao pode aparecer",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "x",
                "conteudo_html": "<p>x</p>",
                "grupo_id": 9,
                "publicado_em": "2026-11-02",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "crosta",
                "titulo": "Crosta",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "em portugues",
                "conteudo_html": "<p>pt</p>",
                "grupo_id": 9,
                "sentidos": ["aroma"],
                "publicado_em": "2026-11-01",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "crust",
                "titulo": "Crust",
                "idioma": "en",
                "secao": "insights",
                "resumo": "in english",
                "conteudo_html": "<p>en</p>",
                "grupo_id": 9,
                "sentidos": ["aroma"],
                "publicado_em": "2026-11-01",
            },
        ]

    monkeypatch.setattr(cms, "fetch_hub_payload", fake_payload)
    monkeypatch.setattr(cms, "fetch_hub_post", lambda slug: None)
    page = TestClient(app).get("/pt/insights/crosta")
    assert page.status_code == 200
    assert "Nao pode aparecer" not in page.text
    assert 'hreflang="en"' in page.text
    assert "/en/insights/crust" in page.text
    english = TestClient(app).get("/en/insights/crust")
    assert "/pt/insights/crosta" in english.text


def test_hub_empty_section(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "hub")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    cms.reset_cache()
    monkeypatch.setattr(cms, "fetch_hub_payload", lambda secao="", idioma="": [])
    portuguese = TestClient(app).get("/pt")
    english = TestClient(app).get("/en/insights")
    now = TestClient(app).get("/en/right-now")
    assert portuguese.status_code == 200
    assert "primeiro texto a caminho" in portuguese.text
    assert "first story on its way" in english.text
    assert "first story on its way" in now.text


def test_hub_keeps_last_good_copy(monkeypatch):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "hub")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    cms.reset_cache()
    calls = {"n": 0}

    def flaky(secao="", idioma=""):
        calls["n"] += 1
        if calls["n"] == 1:
            return [
                {
                    "sistema_destino": "lepain",
                    "status": "publicado",
                    "slug": "fica",
                    "titulo": "Copia boa",
                    "idioma": "pt",
                    "secao": "insights",
                    "resumo": "y",
                    "conteudo_html": "<p>y</p>",
                    "grupo_id": 3,
                    "publicado_em": "2026-11-01",
                }
            ]
        raise OSError("hub fora")

    monkeypatch.setattr(cms, "fetch_hub_payload", flaky)
    assert cms.all_posts()[0]["titulo"] == "Copia boa"
    cms._cache["at"] = 0
    assert cms.all_posts()[0]["titulo"] == "Copia boa"
