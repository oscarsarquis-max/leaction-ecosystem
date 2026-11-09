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


def hub_client(monkeypatch, rows):
    monkeypatch.setenv("LEPAIN_CMS_SOURCE", "hub")
    monkeypatch.setenv("LEPAIN_TODAY", "2026-11-08")
    monkeypatch.delenv("LEPAIN_INSTAGRAM", raising=False)
    cms.reset_cache()
    monkeypatch.setattr(cms, "fetch_hub_payload", lambda secao="", idioma="": rows)
    monkeypatch.setattr(cms, "fetch_hub_post", lambda slug: None)
    return TestClient(app)


def test_en_inherits_pt_issue_number(monkeypatch):
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "segundo",
                "titulo": "Segundo",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "depois",
                "conteudo_html": "<p>depois</p>",
                "grupo_id": 2,
                "publicado_em": "2026-11-04",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "primeiro",
                "titulo": "Primeiro",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "antes",
                "conteudo_html": "<p>antes</p>",
                "grupo_id": 1,
                "publicado_em": "2026-11-01",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "first",
                "titulo": "First",
                "idioma": "en",
                "secao": "insights",
                "resumo": "earlier in english",
                "conteudo_html": "<p>en</p>",
                "grupo_id": 1,
                "publicado_em": "2026-11-05",
            },
        ],
    )
    english = pages.get("/en/insights/first")
    assert english.status_code == 200
    assert "Nº 01" in english.text
    assert "Nº 02" not in english.text
    assert "Nº 01" in pages.get("/pt/insights/primeiro").text
    assert "Nº 02" in pages.get("/pt/insights/segundo").text
    assert "Nº 01" in pages.get("/en/card/first").text
    assert "Nº 01" in pages.get("/pt/card/primeiro").text
    assert "Nº 02" in pages.get("/pt/card/segundo").text


def test_cover_present_and_absent(monkeypatch):
    cover = "https://cdn.example/levain.png"
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "com-capa",
                "titulo": "Com capa",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "foto",
                "conteudo_html": f'<figure class="wide"><img src="{cover}" alt=""></figure><p>massa</p>',
                "imagem_capa": cover,
                "grupo_id": 1,
                "publicado_em": "2026-11-03",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "capa-sem-figura",
                "titulo": "Capa sem figura",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "foto nova",
                "conteudo_html": "<p>sem figura</p>",
                "imagem_capa": "https://cdn.example/outra.png",
                "grupo_id": 8,
                "publicado_em": "2026-11-01",
            },
        ],
    )
    home = pages.get("/pt")
    hero = home.text.split('class="hero-panel"', 1)[1].split("</a>", 1)[0]
    assert f'<img class="cover" src="{cover}"' in hero
    assert 'class="bread"' not in hero
    assert 'class="panel-note"' not in hero
    post = pages.get("/pt/insights/com-capa")
    assert post.text.count(f'<img src="{cover}"') == 1
    assert f'<figure class="wide"><img src="{cover}"' in post.text
    injected = pages.get("/pt/insights/capa-sem-figura")
    assert '<figure class="wide"><img src="https://cdn.example/outra.png"' in injected.text

    bare = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "sem-capa",
                "titulo": "Sem capa",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "so texto",
                "conteudo_html": "<p>so texto</p>",
                "grupo_id": 4,
                "publicado_em": "2026-11-02",
            }
        ],
    )
    home = bare.get("/pt")
    hero = home.text.split('class="hero-panel"', 1)[1].split("</a>", 1)[0]
    assert 'class="bread"' in hero
    assert 'class="panel-note"' in hero
    assert 'class="cover"' not in hero
    missing = bare.get("/pt/insights/sem-capa")
    assert 'class="cover"' not in missing.text
    assert 'class="wide"' not in missing.text


def test_hub_html_has_no_placeholder(monkeypatch):
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "ensaio",
                "titulo": "Ensaio",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "resumo",
                "conteudo_html": "<p>texto</p>",
                "imagem_capa": "https://cdn.example/ensaio.png",
                "grupo_id": 7,
                "publicado_em": "2026-11-02",
                "sentidos": ["aroma"],
            }
        ],
    )
    home = pages.get("/pt")
    post = pages.get("/pt/insights/ensaio")
    assert home.status_code == 200
    assert post.status_code == 200
    assert "[PLACEHOLDER]" not in home.text
    assert "[PLACEHOLDER]" not in post.text
    assert "Editor LePain" in home.text
    assert "Editor LePain" in post.text
    assert "LePain · Bread & Sense" in post.text
    assert "Uma mordida por semana no Instagram. O ensaio inteiro, aqui." in home.text
    assert "Seguir @" not in home.text


def test_follow_button_uses_instagram_handle(monkeypatch):
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "ensaio",
                "titulo": "Ensaio",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "resumo",
                "conteudo_html": "<p>texto</p>",
                "grupo_id": 7,
                "publicado_em": "2026-11-02",
                "sentidos": ["aroma"],
            }
        ],
    )
    monkeypatch.setenv("LEPAIN_INSTAGRAM", "loja.de.paes")
    pt = pages.get("/pt")
    en = pages.get("/en")
    assert pt.status_code == 200
    assert 'href="https://www.instagram.com/loja.de.paes/"' in pt.text
    assert "Seguir @loja.de.paes" in pt.text
    assert "Follow @loja.de.paes" in en.text


def test_post_instagram_link_only_when_the_url_is_set(monkeypatch):
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "com-link",
                "titulo": "Com link",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "resumo",
                "conteudo_html": "<p>texto</p>",
                "grupo_id": 8,
                "publicado_em": "2026-11-02",
                "sentidos": ["sabor"],
                "instagram_url": "https://www.instagram.com/p/AbC123/",
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "sem-link",
                "titulo": "Sem link",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "resumo",
                "conteudo_html": "<p>texto</p>",
                "grupo_id": 9,
                "publicado_em": "2026-11-03",
                "sentidos": ["sabor"],
            },
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "with-link",
                "titulo": "With link",
                "idioma": "en",
                "secao": "insights",
                "resumo": "summary",
                "conteudo_html": "<p>text</p>",
                "grupo_id": 8,
                "publicado_em": "2026-11-02",
                "sentidos": ["sabor"],
                "instagram_url": "https://instagram.com/p/EnPost/",
            },
        ],
    )
    linked = pages.get("/pt/insights/com-link")
    plain = pages.get("/pt/insights/sem-link")
    english = pages.get("/en/insights/with-link")
    assert linked.status_code == 200
    assert 'href="https://www.instagram.com/p/AbC123/"' in linked.text
    assert "Ver no Instagram ↗" in linked.text
    assert "/card/" not in linked.text
    assert "VER O CARD" not in linked.text
    assert plain.status_code == 200
    assert "Ver no Instagram" not in plain.text
    assert "/card/" not in plain.text
    assert "See on Instagram ↗" in english.text
    assert 'href="https://instagram.com/p/EnPost/"' in english.text


def test_card_uses_short_summary_when_instagram_caption_is_long(monkeypatch):
    caption = (
        "A receita da avó dizia coloque farinha até a massa ficar no ponto. "
        * 8
        + "#LePain #PãoEMemória #MemóriaAfetiva"
    )
    pages = hub_client(
        monkeypatch,
        [
            {
                "sistema_destino": "lepain",
                "status": "publicado",
                "slug": "casa",
                "titulo": "O pão que guarda uma casa",
                "idioma": "pt",
                "secao": "insights",
                "resumo": "Um cheiro conhecido traz de volta uma cozinha.",
                "resumo_instagram": caption,
                "conteudo_html": "<p>texto</p>",
                "grupo_id": 3,
                "publicado_em": "2026-11-08",
                "sentidos": ["memoria"],
            }
        ],
    )
    card = pages.get("/pt/card/casa")
    assert card.status_code == 200
    assert "Um cheiro conhecido traz de volta uma cozinha." in card.text
    assert 'data-summary="Um cheiro conhecido traz de volta uma cozinha."' in card.text
    assert caption not in card.text
    assert 'content="Um cheiro conhecido traz de volta uma cozinha."' in card.text
