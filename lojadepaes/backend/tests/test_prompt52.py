from io import BytesIO

from PIL import Image
from tests.admin_client import admin_client, login

assert admin_client


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 18), (210, 190, 150)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _headers(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def _publish(admin_client, csrf: str, title: str, summary: str, ingredients: list[str], steps: list[str], feature: bool = False) -> dict:
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": title,
            "summary": summary,
            "featured_image_alt": "Prato",
            "ingredients": ingredients,
            "steps": steps,
        },
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/image",
        headers=_headers(csrf),
        files={"file": ("prato.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Prato"},
    )
    path = "publish-featured" if feature else "publish"
    published = admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/{path}",
        headers=_headers(csrf),
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_catalog_search_covers_title_ingredient_and_method(admin_client) -> None:
    csrf = login(admin_client)
    featured = _publish(
        admin_client,
        csrf,
        "Torrada da casa",
        "Fatias com azeite e tomate.",
        ["2 fatias de pão", "azeite"],
        ["Tostar o pão"],
        feature=True,
    )
    other = _publish(
        admin_client,
        csrf,
        "Pudim de pão",
        "Sobremesa com leite.",
        ["pão amanhecido", "leite"],
        ["Leve ao forno até dourar."],
    )
    draft = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Rascunho com azeite", "summary": "ainda não"},
    ).json()
    listing = admin_client.get("/api/v1/catalog/week-recipes").json()
    assert listing["total"] == 2
    slugs = [item["slug"] for item in listing["items"]]
    assert featured["slug"] in slugs
    assert other["slug"] in slugs
    assert draft["slug"] not in slugs
    assert listing["items"][0]["href"].startswith("/receitas/")

    by_title = admin_client.get("/api/v1/catalog/week-recipes", params={"q": "pudim"}).json()
    assert [item["slug"] for item in by_title["items"]] == [other["slug"]]

    by_ingredient = admin_client.get("/api/v1/catalog/week-recipes", params={"q": "azeite"}).json()
    assert [item["slug"] for item in by_ingredient["items"]] == [featured["slug"]]

    by_method = admin_client.get("/api/v1/catalog/week-recipes", params={"q": "dourar"}).json()
    assert [item["slug"] for item in by_method["items"]] == [other["slug"]]

    empty = admin_client.get("/api/v1/catalog/week-recipes", params={"q": "wasabi"}).json()
    assert empty["total"] == 0
    assert empty["items"] == []

    page1 = admin_client.get("/api/v1/catalog/week-recipes", params={"page": 1, "page_size": 1}).json()
    page2 = admin_client.get("/api/v1/catalog/week-recipes", params={"page": 2, "page_size": 1}).json()
    assert page1["total"] == 2
    assert len(page1["items"]) == 1
    assert len(page2["items"]) == 1
    assert page1["items"][0]["slug"] != page2["items"][0]["slug"]

    home = admin_client.get("/api/v1/catalog/week-recipe").json()["recipe"]
    assert home["slug"] == featured["slug"]
    assert home["title"] == "Torrada da casa"
    assert home["summary"] == "Fatias com azeite e tomate."
