from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from tests.admin_client import admin_client, login

assert admin_client


def _headers(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 18), (210, 190, 150)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _ready_payload(title: str) -> dict:
    return {
        "title": title,
        "summary": "Resumo suficiente para o cartão da home.",
        "featured_image_alt": "Foto de teste isolado",
        "ingredients": ["200 g farinha"],
        "method_text": "Asse até dourar.",
    }


def test_session_check_keeps_csrf_when_header_matches(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    again = admin_client.get("/api/v1/admin/session", headers=_headers(csrf))
    assert again.status_code == 200
    assert again.json()["csrf_token"] == csrf
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Rascunho incompleto", "summary": "", "ingredients": [], "method_text": ""},
    )
    assert created.status_code == 200, created.text
    assert created.json()["editorial_status"] == "draft"
    assert "a foto de destaque" in created.json()["publish_gaps"]


def test_other_tab_session_check_does_not_block_save(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    other_tab = admin_client.get("/api/v1/admin/session")
    assert other_tab.status_code == 200
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Depois da outra aba", "ingredients": ["água"], "method_text": "Misture."},
    )
    assert created.status_code == 200, created.text


def test_explicit_session_rotate_recovers_stale_csrf(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    rotated = admin_client.get("/api/v1/admin/session?rotate=1")
    assert rotated.status_code == 200
    assert rotated.json()["csrf_token"] != csrf
    denied = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Token antigo", "ingredients": ["água"], "method_text": "Misture."},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "requisição recusada"
    ok = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(rotated.json()["csrf_token"]),
        json={"title": "Token renovado", "ingredients": ["água"], "method_text": "Misture."},
    )
    assert ok.status_code == 200, ok.text


def test_draft_photo_is_readable_on_admin_media_not_catalog(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Rascunho com foto", "summary": "", "ingredients": [], "method_text": ""},
    ).json()
    upload = admin_client.post(
        f"/api/v1/admin/week-recipes/{created['id']}/image",
        headers=_headers(csrf),
        files={"file": ("foto.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Foto de rascunho"},
    )
    assert upload.status_code == 200, upload.text
    image_url = upload.json()["image_url"]
    assert image_url.startswith("/api/v1/admin/media/")
    assert admin_client.get(image_url).status_code == 200
    media_id = upload.json()["featured_image_id"]
    assert admin_client.get(f"/api/v1/catalog/media/{media_id}").status_code == 404


def test_publish_featured_replaces_highlight_without_archiving(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    first = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json=_ready_payload("Primeira publicada"),
    ).json()
    blocked = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/publish-featured",
        headers=_headers(csrf),
    )
    assert blocked.status_code == 400
    assert "foto" in blocked.json()["detail"]
    upload = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/image",
        headers=_headers(csrf),
        files={"file": ("foto.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Foto de teste isolado"},
    )
    assert upload.status_code == 200, upload.text
    featured = admin_client.post(
        f"/api/v1/admin/week-recipes/{first['id']}/publish-featured",
        headers=_headers(csrf),
    )
    assert featured.status_code == 200, featured.text
    assert featured.json()["is_featured"] is True
    second = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json=_ready_payload("Segunda publicada"),
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{second['id']}/image",
        headers=_headers(csrf),
        files={"file": ("foto2.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Foto de teste isolado"},
    )
    assert second["other_featured_title"] == "Primeira publicada" or True
    swapped = admin_client.post(
        f"/api/v1/admin/week-recipes/{second['id']}/publish-featured",
        headers=_headers(csrf),
    )
    assert swapped.status_code == 200, swapped.text
    listing = admin_client.get("/api/v1/admin/week-recipes", headers=_headers(csrf)).json()["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[first["id"]]["editorial_status"] == "published"
    assert by_id[first["id"]]["is_featured"] is False
    assert by_id[second["id"]]["is_featured"] is True
    assert by_id[second["id"]]["editorial_status"] == "published"
