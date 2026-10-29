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


def test_incomplete_draft_saves_and_publish_names_missing_alt(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Rascunho 64",
            "summary": "Preparo preenchido no ensaio isolado.",
            "featured_image_alt": "",
            "prep_time_text": "25 minutos",
            "yield_text": "2 porções",
            "ingredients": ["pão", "azeite"],
            "method_text": "Asse até dourar. Tempo 25 minutos.",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    recipe_id = body["id"]
    assert body["editorial_status"] == "draft"
    assert "o texto alternativo da foto" in body["publish_gaps"]
    opened = admin_client.get(f"/api/v1/admin/week-recipes/{recipe_id}", headers=_headers(csrf))
    assert opened.status_code == 200
    assert opened.json()["method_text"].startswith("Asse até dourar")
    assert opened.json()["prep_time_text"] == "25 minutos"
    assert opened.json()["yield_text"] == "2 porções"
    blocked = admin_client.post(
        f"/api/v1/admin/week-recipes/{recipe_id}/publish",
        headers=_headers(csrf),
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "para publicar, complete: a foto de destaque, o texto alternativo da foto"
    again = admin_client.get(f"/api/v1/admin/week-recipes/{recipe_id}", headers=_headers(csrf))
    assert again.json()["editorial_status"] == "draft"
    assert again.json()["title"] == "Rascunho 64"


def test_failed_publish_does_not_drop_existing_featured(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    featured = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Destaque anterior 64",
            "summary": "Receita já publicada no ensaio.",
            "featured_image_alt": "Foto isolada do destaque",
            "ingredients": ["pão"],
            "method_text": "Sirva.",
        },
    ).json()
    admin_client.post(
        f"/api/v1/admin/week-recipes/{featured['id']}/image",
        headers=_headers(csrf),
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
        data={"alt": "Foto isolada do destaque"},
    )
    ok = admin_client.post(
        f"/api/v1/admin/week-recipes/{featured['id']}/publish-featured",
        headers=_headers(csrf),
    )
    assert ok.status_code == 200, ok.text
    draft = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Candidata incompleta 64",
            "summary": "Tem preparo, sem alt.",
            "featured_image_alt": "",
            "ingredients": ["água"],
            "method_text": "Ferva.",
        },
    ).json()
    failed = admin_client.post(
        f"/api/v1/admin/week-recipes/{draft['id']}/publish-featured",
        headers=_headers(csrf),
    )
    assert failed.status_code == 400
    listing = admin_client.get("/api/v1/admin/week-recipes", headers=_headers(csrf)).json()["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[featured["id"]]["is_featured"] is True
    assert by_id[featured["id"]]["editorial_status"] == "published"
    assert by_id[draft["id"]]["editorial_status"] == "draft"
    assert by_id[draft["id"]]["is_featured"] is False


def test_second_create_does_not_duplicate_when_id_exists(admin_client: TestClient) -> None:
    csrf = login(admin_client)
    first = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={"title": "Uma vez 64", "ingredients": ["sal"], "method_text": "Misture."},
    ).json()
    updated = admin_client.put(
        f"/api/v1/admin/week-recipes/{first['id']}",
        headers=_headers(csrf),
        json={
            "title": "Uma vez 64",
            "summary": "Atualização do mesmo id.",
            "ingredients": ["sal", "água"],
            "method_text": "Misture de novo.",
        },
    )
    assert updated.status_code == 200, updated.text
    listing = admin_client.get("/api/v1/admin/week-recipes", headers=_headers(csrf)).json()["items"]
    titles = [item["title"] for item in listing if item["title"].startswith("Uma vez 64")]
    assert titles == ["Uma vez 64"]
    assert updated.json()["id"] == first["id"]
    assert updated.json()["ingredients"] == ["sal", "água"]
