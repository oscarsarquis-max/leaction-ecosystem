from app.domain.week_recipes import method_text_to_steps, steps_to_method_text
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

assert admin_client


def _headers(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def test_legacy_steps_open_as_single_method_and_resave(admin_client, db: Session) -> None:
    del db
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Antiga com passos",
            "summary": "Receita legada com passos estruturados.",
            "ingredients": ["200 g farinha", "", "1 ovo"],
            "steps": ["1. Misture a farinha", "2. Sove a massa", "Asse até dourar"],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["ingredients"] == ["200 g farinha", "1 ovo"]
    assert body["method_text"] == "1. Misture a farinha\n\n2. Sove a massa\n\nAsse até dourar"
    assert body["steps"] == ["1. Misture a farinha", "2. Sove a massa", "Asse até dourar"]
    again = admin_client.put(
        f"/api/v1/admin/week-recipes/{body['id']}",
        headers=_headers(csrf),
        json={
            "title": body["title"],
            "summary": body["summary"],
            "ingredients": body["ingredients"],
            "method_text": body["method_text"],
        },
    )
    assert again.status_code == 200, again.text
    saved = again.json()
    assert saved["method_text"] == body["method_text"]
    assert saved["steps"] == body["steps"]
    third = admin_client.put(
        f"/api/v1/admin/week-recipes/{body['id']}",
        headers=_headers(csrf),
        json={
            "title": body["title"],
            "summary": body["summary"],
            "ingredients": body["ingredients"],
            "method_text": body["method_text"],
        },
    ).json()
    assert third["steps"] == body["steps"]
    assert "1. 1." not in third["method_text"]


def test_method_text_is_source_of_truth(admin_client) -> None:
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/week-recipes",
        headers=_headers(csrf),
        json={
            "title": "Texto único",
            "summary": "Preparo colado em um campo só.",
            "ingredients": ["água"],
            "steps": ["este passo antigo deve ceder"],
            "method_text": "Aqueça o forno.\n\nAsse 20 minutos.",
        },
    ).json()
    assert created["method_text"] == "Aqueça o forno.\n\nAsse 20 minutos."
    assert created["steps"] == ["Aqueça o forno.", "Asse 20 minutos."]


def test_week_recipes_still_need_admin(admin_client) -> None:
    assert admin_client.get("/api/v1/admin/week-recipes").status_code == 401


def test_conversion_helpers_do_not_invent_units() -> None:
    assert steps_to_method_text(["1. Abrir", "Rechear"]) == "1. Abrir\n\nRechear"
    assert method_text_to_steps("1. Abrir\n\nRechear") == ["1. Abrir", "Rechear"]
