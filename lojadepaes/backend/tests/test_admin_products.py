import io
from collections.abc import Iterator

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session
from tests.admin_client import (
    TEST_ADMIN_HASH,
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USER,
    TEST_SESSION_SECRET,
    login,
)

assert TEST_ADMIN_PASSWORD


def _image_bytes(fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), (160, 110, 70)).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def product_client(db: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    del db
    monkeypatch.setenv("LOJADEPAES_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("LOJADEPAES_ADMIN_PASSWORD_HASH", TEST_ADMIN_HASH)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    reset_engine()


def _auth(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": login(client)}


def _base_payload(**overrides):
    payload = {
        "name": "Pão de fermentação natural",
        "short_description": "Crosta firme e miolo aberto.",
        "featured_image_alt": "Pão rústico sobre pano de linho",
        "ingredients": [
            {"name": "Farinha de trigo"},
            {"name": "Água"},
            {"name": "Levain"},
            {"name": "Sal"},
        ],
        "variants": [
            {
                "display_name": "500 g",
                "presentation_type": "weight",
                "net_weight_grams": 500,
                "price_text": "24,90",
                "is_active": True,
            },
            {
                "display_name": "800 g",
                "presentation_type": "weight",
                "net_weight_grams": 800,
                "price_text": "32,00",
                "is_active": True,
            },
        ],
    }
    payload.update(overrides)
    return payload


def _create_ready(client: TestClient, headers: dict[str, str], payload: dict | None = None) -> dict:
    created = client.post("/api/v1/admin/products", json=payload or _base_payload(), headers=headers)
    assert created.status_code == 200, created.text
    product_id = created.json()["id"]
    uploaded = client.post(
        f"/api/v1/admin/products/{product_id}/image",
        headers=headers,
        files={"file": ("pao.png", _image_bytes(), "image/png")},
        data={"alt": "Pão rústico sobre pano de linho"},
    )
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()


def test_admin_products_require_auth(product_client: TestClient) -> None:
    assert product_client.get("/api/v1/admin/products").status_code == 401


def test_upload_requires_csrf(product_client: TestClient) -> None:
    headers = _auth(product_client)
    created = product_client.post(
        "/api/v1/admin/products",
        json={"name": "Rascunho", "ingredients": [], "variants": []},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    blocked = product_client.post(
        f"/api/v1/admin/products/{created.json()['id']}/image",
        files={"file": ("pao.png", _image_bytes(), "image/png")},
    )
    assert blocked.status_code == 403


def test_draft_not_public_until_published(product_client: TestClient) -> None:
    headers = _auth(product_client)
    ready = _create_ready(product_client, headers)
    slug = ready["slug"]
    public = product_client.get("/api/v1/catalog/products")
    assert public.status_code == 200
    assert public.json()["items"] == []
    assert product_client.get(f"/api/v1/catalog/products/{slug}").status_code == 404
    media_id = ready["featured_image"]["id"]
    assert product_client.get(f"/api/v1/catalog/media/{media_id}").status_code == 404
    published = product_client.post(f"/api/v1/admin/products/{ready['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    listed = product_client.get("/api/v1/catalog/products")
    assert listed.json()["total"] == 1
    item = listed.json()["items"][0]
    assert item["slug"] == slug
    assert item["price_is_from"] is True
    assert item["from_price"]["cents"] == 2490
    detail = product_client.get(f"/api/v1/catalog/products/{slug}").json()
    assert [row["name"] for row in detail["ingredients"]] == [
        "Farinha de trigo",
        "Água",
        "Levain",
        "Sal",
    ]
    assert {row["display_name"]: row["price"]["cents"] for row in detail["variants"]} == {
        "500 g": 2490,
        "800 g": 3200,
    }
    assert "updated_by_ref" not in detail
    assert product_client.get(f"/api/v1/catalog/media/{media_id}").status_code == 200


def test_publish_requires_complete_product(product_client: TestClient) -> None:
    headers = _auth(product_client)
    created = product_client.post(
        "/api/v1/admin/products",
        json={"name": "Incompleto", "ingredients": [], "variants": []},
        headers=headers,
    )
    assert created.status_code == 200
    failed = product_client.post(
        f"/api/v1/admin/products/{created.json()['id']}/publish", headers=headers
    )
    assert failed.status_code == 400
    assert "complete" in failed.json()["detail"]


def test_variant_rules_and_pack(product_client: TestClient) -> None:
    headers = _auth(product_client)
    unit = _create_ready(
        product_client,
        headers,
        _base_payload(
            name="Broa de milho",
            variants=[
                {
                    "display_name": "1 unidade",
                    "presentation_type": "pack",
                    "units_per_pack": 1,
                    "price_text": "8,00",
                    "is_active": True,
                }
            ],
        ),
    )
    pack = _create_ready(
        product_client,
        headers,
        _base_payload(
            name="Pão de leite",
            variants=[
                {
                    "display_name": "Pacote com 6 unidades",
                    "presentation_type": "pack",
                    "units_per_pack": 6,
                    "price_text": "18,00",
                    "is_active": True,
                }
            ],
        ),
    )
    product_client.post(f"/api/v1/admin/products/{unit['id']}/publish", headers=headers)
    product_client.post(f"/api/v1/admin/products/{pack['id']}/publish", headers=headers)
    catalog = product_client.get("/api/v1/catalog/products").json()["items"]
    names = {item["name"]: item for item in catalog}
    assert names["Broa de milho"]["price_is_from"] is False
    assert names["Pão de leite"]["variants"][0]["pack_label"] == "pacote com 6 unidades"
    duplicate = product_client.post(
        "/api/v1/admin/products",
        json=_base_payload(
            name="Duplicado",
            variants=[
                {
                    "display_name": "500 g",
                    "presentation_type": "weight",
                    "net_weight_grams": 500,
                    "price_text": "10,00",
                    "is_active": True,
                },
                {
                    "display_name": "Meio quilo",
                    "presentation_type": "weight",
                    "net_weight_grams": 500,
                    "price_text": "11,00",
                    "is_active": True,
                },
            ],
        ),
        headers=headers,
    )
    assert duplicate.status_code == 400


def test_image_validation_and_replace_keeps_previous(product_client: TestClient) -> None:
    headers = _auth(product_client)
    ready = _create_ready(product_client, headers)
    first_id = ready["featured_image"]["id"]
    too_big = product_client.post(
        f"/api/v1/admin/products/{ready['id']}/image",
        headers=headers,
        files={"file": ("big.png", b"x" * (8 * 1024 * 1024 + 10), "image/png")},
    )
    assert too_big.status_code == 400
    svg = product_client.post(
        f"/api/v1/admin/products/{ready['id']}/image",
        headers=headers,
        files={"file": ("x.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml")},
    )
    assert svg.status_code == 400
    after = product_client.get(f"/api/v1/admin/products/{ready['id']}", headers=headers).json()
    assert after["featured_image"]["id"] == first_id
    second = product_client.post(
        f"/api/v1/admin/products/{ready['id']}/image",
        headers=headers,
        files={"file": ("pao.jpg", _image_bytes("JPEG"), "image/jpeg")},
    )
    assert second.status_code == 200
    assert second.json()["featured_image"]["id"] != first_id


def test_unavailability_and_archive_leave_catalog(product_client: TestClient) -> None:
    headers = _auth(product_client)
    ready = _create_ready(product_client, headers)
    product_client.post(f"/api/v1/admin/products/{ready['id']}/publish", headers=headers)
    hidden = product_client.post(
        f"/api/v1/admin/products/{ready['id']}/availability",
        json={"is_available": False},
        headers=headers,
    )
    assert hidden.status_code == 200
    detail = product_client.get(f"/api/v1/catalog/products/{ready['slug']}").json()
    assert detail["is_available"] is False
    archived = product_client.post(
        f"/api/v1/admin/products/{ready['id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert product_client.get("/api/v1/catalog/products").json()["items"] == []
    assert product_client.get(f"/api/v1/catalog/products/{ready['slug']}").status_code == 404


def test_published_cannot_lose_all_variants(product_client: TestClient) -> None:
    headers = _auth(product_client)
    ready = _create_ready(product_client, headers)
    product_client.post(f"/api/v1/admin/products/{ready['id']}/publish", headers=headers)
    current = product_client.get(f"/api/v1/admin/products/{ready['id']}", headers=headers).json()
    wiped = product_client.put(
        f"/api/v1/admin/products/{ready['id']}",
        json=_base_payload(variants=[], expected_updated_at=current["updated_at"]),
        headers=headers,
    )
    assert wiped.status_code == 400
    stale = product_client.put(
        f"/api/v1/admin/products/{ready['id']}",
        json=_base_payload(expected_updated_at="2000-01-01T00:00:00Z"),
        headers=headers,
    )
    assert stale.status_code == 409
