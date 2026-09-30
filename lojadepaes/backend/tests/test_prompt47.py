from io import BytesIO
from uuid import uuid4

from app.domain.recipe_bases import create_recipe_base
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from PIL import Image
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

assert admin_client


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 18), (210, 190, 150)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _headers(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def _published_bread(db: Session) -> Product:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 47")
    product = Product(
        name="Pão da casa",
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="crosta",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    db.add(
        ProductVariant(
            product_id=product.id,
            display_name="500 g",
            presentation_type="weight",
            net_weight_grams=500,
            physical_units=1,
            price_cents=2490,
            currency="BRL",
            is_active=True,
        )
    )
    db.flush()
    db.commit()
    return product


def test_draft_is_not_public_and_needs_admin(admin_client, db: Session) -> None:
    del db
    assert admin_client.get("/api/v1/admin/week-recipes").status_code == 401
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "<b>Rascunho</b>", "summary": "ainda incompleto"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["title"] == "Rascunho"
    assert "<" not in body["title"]
    assert body["editorial_status"] == "draft"
    assert body["is_featured"] is False
    slug = body["slug"]
    assert admin_client.get(f"/api/v1/catalog/week-recipes/{slug}").status_code == 404
    featured = admin_client.get("/api/v1/catalog/week-recipe")
    assert featured.status_code == 200
    assert featured.json()["recipe"] is None
    admin_client.cookies.clear()
    assert admin_client.get("/api/v1/admin/week-recipes").status_code == 401


def test_publish_feature_and_atomic_swap(admin_client, db: Session) -> None:
    csrf = login(admin_client)
    bread = _published_bread(db)
    first = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Primeira",
            "summary": "Resumo da primeira receita da semana para a vitrine.",
            "featured_image_alt": "Prato",
            "ingredients": ["1 fatia de pão"],
            "steps": ["Tostar o pão"],
            "product_ids": [str(bread.id)],
        },
    ).json()
    upload = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/image",
        headers=_headers(csrf),
        files={"file": ("prato.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Prato"},
    )
    assert upload.status_code == 200, upload.text
    published = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/publish",
        headers=_headers(csrf),
    )
    assert published.status_code == 200
    assert published.json()["is_featured"] is False
    assert admin_client.get("/api/v1/catalog/week-recipe").json()["recipe"] is None
    featured = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/feature",
        headers=_headers(csrf),
    )
    assert featured.status_code == 200
    home = admin_client.get("/api/v1/catalog/week-recipe").json()["recipe"]
    assert home["title"] == "Primeira"
    assert home["href"] == "/receitas/primeira"
    assert home["breads"][0]["href"] == f"/paes/{bread.slug}"
    page = admin_client.get("/api/v1/catalog/week-recipes/primeira")
    assert page.status_code == 200
    media_id = featured.json()["featured_image_id"]
    assert admin_client.get(f"/api/v1/catalog/media/{media_id}").status_code == 200

    second = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Segunda",
            "summary": "Outra receita publicada para trocar o destaque.",
            "featured_image_alt": "Outro prato",
            "ingredients": ["azeite"],
            "steps": ["Regar"],
        },
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{second['id']}/image",
        headers=_headers(csrf),
        files={"file": ("prato2.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Outro prato"},
    )
    admin_client.post(f"/api/v1/admin/week-recipes/{second['id']}/publish", headers=_headers(csrf))
    swapped = admin_client.post(
        f"/api/v1/admin/week-recipes/{second['id']}/feature",
        headers=_headers(csrf),
    )
    assert swapped.status_code == 200
    assert swapped.json()["is_featured"] is True
    listing = admin_client.get("/api/v1/admin/week-recipes", headers=_headers(csrf)).json()["items"]
    featured_ids = [item["id"] for item in listing if item["is_featured"]]
    assert featured_ids == [second["id"]]
    assert admin_client.get("/api/v1/catalog/week-recipe").json()["recipe"]["slug"] == "segunda"

    admin_client.post(f"/api/v1/admin/week-recipes/{second['id']}/unfeature", headers=_headers(csrf))
    assert admin_client.get("/api/v1/catalog/week-recipe").json()["recipe"] is None
    admin_client.post(f"/api/v1/admin/week-recipes/{first['id']}/archive", headers=_headers(csrf))
    assert admin_client.get("/api/v1/catalog/week-recipes/primeira").status_code == 404


def test_publish_requires_minimum_content(admin_client) -> None:
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Incompleta"},
    ).json()
    response = admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/publish",
        headers=_headers(csrf),
    )
    assert response.status_code == 400
    assert "resumo" in response.json()["detail"]
    assert "foto" in response.json()["detail"]


def test_unpublished_bread_keeps_name_without_link(admin_client, db: Session) -> None:
    csrf = login(admin_client)
    bread = _published_bread(db)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Com pão",
            "summary": "Usa um pão que depois sai da vitrine.",
            "featured_image_alt": "Prato",
            "ingredients": ["pão"],
            "steps": ["servir"],
            "product_ids": [str(bread.id)],
        },
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/image",
        headers=_headers(csrf),
        files={"file": ("prato.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Prato"},
    )
    admin_client.post(f"/api/v1/admin/week-recipes/{created['id']}/publish", headers=_headers(csrf))
    admin_client.post(f"/api/v1/admin/week-recipes/{created['id']}/feature", headers=_headers(csrf))
    bread.editorial_status = EditorialStatus.DRAFT.value
    db.commit()
    public = admin_client.get("/api/v1/catalog/week-recipes/com-pao").json()
    assert public["breads"][0]["name"] == "Pão da casa"
    assert public["breads"][0]["href"] is None


def test_recipe_is_not_a_showcase_product(admin_client, db: Session) -> None:
    del db
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Fora da grade",
            "summary": "Não deve aparecer como pão da vitrine.",
            "featured_image_alt": "Prato",
            "ingredients": ["azeite"],
            "steps": ["misturar"],
        },
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/image",
        headers=_headers(csrf),
        files={"file": ("prato.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Prato"},
    )
    admin_client.post(f"/api/v1/admin/week-recipes/{created['id']}/publish", headers=_headers(csrf))
    admin_client.post(f"/api/v1/admin/week-recipes/{created['id']}/feature", headers=_headers(csrf))
    showcase = admin_client.get("/api/v1/catalog/showcase").json()
    slugs = [item["slug"] for item in showcase.get("items", [])]
    assert "fora-da-grade" not in slugs
