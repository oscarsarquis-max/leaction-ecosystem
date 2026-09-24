from collections.abc import Iterator
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.db.session import reset_engine
from app.main import create_app
from app.models.products import Product
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_HASH, TEST_ADMIN_USER, TEST_SESSION_SECRET
from tests.test_admin_products import _auth, _base_payload, _create_ready


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


def _publish(client: TestClient, headers: dict[str, str], name: str) -> dict:
    payload = _base_payload(name=name)
    ready = _create_ready(client, headers, payload)
    published = client.post(f"/api/v1/admin/products/{ready['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    return published.json()


def test_showcase_requires_auth(product_client: TestClient) -> None:
    assert product_client.get("/api/v1/admin/showcase").status_code == 401
    assert product_client.put("/api/v1/admin/showcase", json={"slots": []}).status_code == 401


def test_publish_places_on_first_empty_showcase_slot(product_client: TestClient) -> None:
    headers = _auth(product_client)
    published = _publish(product_client, headers, "Pão na vitrine")
    catalog = product_client.get("/api/v1/catalog/products").json()
    assert catalog["total"] == 1
    assert catalog["items"][0]["slug"] == published["slug"]
    showcase = product_client.get("/api/v1/catalog/showcase").json()
    assert [item["slug"] for item in showcase["items"]] == [published["slug"]]
    assert showcase["total"] == 1
    assert published["showcase_position"] == 1


def test_ten_slots_order_and_no_duplicate_product(product_client: TestClient) -> None:
    headers = _auth(product_client)
    created = [_publish(product_client, headers, f"Pão vitrine {index}") for index in range(1, 11)]
    slots = [
        {"position": index, "product_id": created[index - 1]["id"]} for index in range(1, 11)
    ]
    saved = product_client.put("/api/v1/admin/showcase", json={"slots": slots}, headers=headers)
    assert saved.status_code == 200, saved.text
    public = product_client.get("/api/v1/catalog/showcase").json()
    assert [item["name"] for item in public["items"]] == [f"Pão vitrine {index}" for index in range(1, 11)]
    assert public["total"] == 10
    duplicate = product_client.put(
        "/api/v1/admin/showcase/slots/2",
        json={"product_id": created[0]["id"]},
        headers=headers,
    )
    assert duplicate.status_code == 400


def test_draft_and_archive_stay_off_public_showcase(
    product_client: TestClient, db: Session
) -> None:
    headers = _auth(product_client)
    draft = _create_ready(product_client, headers, _base_payload(name="Rascunho vitrine"))
    live = _publish(product_client, headers, "Publicado vitrine")
    product_client.put(
        "/api/v1/admin/showcase/slots/1",
        json={"product_id": draft["id"]},
        headers=headers,
    )
    product_client.put(
        "/api/v1/admin/showcase/slots/2",
        json={"product_id": live["id"]},
        headers=headers,
    )
    public = product_client.get("/api/v1/catalog/showcase").json()
    assert [item["slug"] for item in public["items"]] == [live["slug"]]
    archived = product_client.post(f"/api/v1/admin/products/{live['id']}/archive", headers=headers)
    assert archived.status_code == 200
    after = product_client.get("/api/v1/catalog/showcase").json()
    assert after["items"] == []


def test_remove_slot_keeps_product_and_move_reorders(product_client: TestClient, db: Session) -> None:
    headers = _auth(product_client)
    first = _publish(product_client, headers, "Primeiro na vitrine")
    second = _publish(product_client, headers, "Segundo na vitrine")
    product_client.put(
        "/api/v1/admin/showcase/slots/1",
        json={"product_id": first["id"]},
        headers=headers,
    )
    product_client.put(
        "/api/v1/admin/showcase/slots/2",
        json={"product_id": second["id"]},
        headers=headers,
    )
    moved = product_client.post(
        "/api/v1/admin/showcase/slots/2/move",
        json={"direction": "up"},
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    public = product_client.get("/api/v1/catalog/showcase").json()
    assert [item["name"] for item in public["items"]] == ["Segundo na vitrine", "Primeiro na vitrine"]
    cleared = product_client.put(
        "/api/v1/admin/showcase/slots/1",
        json={"product_id": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    still_there = db.get(Product, UUID(second["id"]))
    assert still_there is not None
    assert still_there.editorial_status == "published"
    leftover = product_client.get("/api/v1/catalog/showcase").json()
    assert [item["name"] for item in leftover["items"]] == ["Segundo na vitrine", "Primeiro na vitrine"]


def test_showcase_exposes_caption_summary_and_ingredients(product_client: TestClient) -> None:
    headers = _auth(product_client)
    payload = _base_payload(
        name="Pão da vitrine completa",
        featured_image_alt="Pão rústico sobre pano de linho",
        featured_image_caption="Fatia com raspas de limão.",
    )
    ready = _create_ready(product_client, headers, payload)
    published = product_client.post(f"/api/v1/admin/products/{ready['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    assigned = product_client.put(
        "/api/v1/admin/showcase/slots/1",
        json={"product_id": published.json()["id"]},
        headers=headers,
    )
    assert assigned.status_code == 200, assigned.text
    public = product_client.get("/api/v1/catalog/showcase")
    assert public.headers.get("cache-control") == "no-store"
    item = public.json()["items"][0]
    assert item["short_description"] == "Crosta firme e miolo aberto."
    assert item["image_alt"] == "Pão rústico sobre pano de linho"
    assert item["image_caption"] == "Fatia com raspas de limão."
    assert [row["name"] for row in item["ingredients"]] == [
        "Farinha de trigo",
        "Água",
        "Levain",
        "Sal",
    ]
    assert "recipe_base_id" not in item


def test_unavailable_published_product_remains_visible(product_client: TestClient) -> None:
    headers = _auth(product_client)
    live = _publish(product_client, headers, "Pão pausado na vitrine")
    product_client.put(
        "/api/v1/admin/showcase/slots/1",
        json={"product_id": live["id"]},
        headers=headers,
    )
    paused = product_client.post(
        f"/api/v1/admin/products/{live['id']}/availability",
        json={"is_available": False},
        headers=headers,
    )
    assert paused.status_code == 200
    public = product_client.get("/api/v1/catalog/showcase").json()
    assert public["items"][0]["is_available"] is False
    assert public["items"][0]["name"] == "Pão pausado na vitrine"


def test_eleventh_published_stays_off_showcase(product_client: TestClient) -> None:
    headers = _auth(product_client)
    created = [_publish(product_client, headers, f"Pão vitrine extra {index}") for index in range(1, 12)]
    showcase = product_client.get("/api/v1/catalog/showcase").json()
    catalog = product_client.get("/api/v1/catalog/products").json()
    assert showcase["total"] == 10
    assert catalog["total"] == 11
    extra = product_client.get(f"/api/v1/admin/products/{created[-1]['id']}", headers=headers).json()
    assert extra["showcase_position"] is None
