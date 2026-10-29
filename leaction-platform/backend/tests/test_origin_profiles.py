from app.services.origin_profiles import (
    DEFAULT_ORIGIN,
    category_belongs_to_origin,
    origin_categories,
    resolve_origin,
)
from app.services.multivendor_orchestrator import MultivendorOrchestrator


def test_default_and_blank_origin_is_legacy_it():
    assert resolve_origin()["origin"] == DEFAULT_ORIGIN
    assert resolve_origin(query_origin="")["origin"] == "legado"
    cats = origin_categories("legado")
    assert cats == ("formacao", "equipamentos", "software")
    listed = {row["id"] for row in MultivendorOrchestrator.list_categories()}
    assert listed == set(cats)
    assert "vinhos" not in listed


def test_app_id_maps_loja_and_beats_query():
    resolved = resolve_origin(app_id="lojadepaes", query_origin="legado")
    assert resolved["ok"] is True
    assert resolved["origin"] == "lojadepaes"
    assert origin_categories("lojadepaes") == (
        "vinhos",
        "queijos",
        "frios",
        "azeites",
        "cervejas",
        "batatas",
    )
    assert category_belongs_to_origin("vinhos", "lojadepaes")
    assert not category_belongs_to_origin("formacao", "lojadepaes")
    assert not category_belongs_to_origin("vinhos", "legado")


def test_unknown_and_unpublished_origins_are_explicit():
    unknown = resolve_origin(query_origin="outro-tenant")
    assert unknown["ok"] is False
    assert unknown["origin"] is None
    assert unknown["error"] == "origem não reconhecida"
    education = resolve_origin(query_origin="educacao")
    assert education["ok"] is False
    assert education["error"] == "origem não publicada"
    bad_app = resolve_origin(app_id="inove4us")
    assert bad_app["ok"] is False


def test_legacy_search_rejects_culinary_category():
    result = MultivendorOrchestrator().search_all_vendors(None, category="vinhos", origin="legado")
    assert result["offers"] == []
    assert "não pertence" in (result.get("notice") or "")


def test_loja_profile_does_not_use_it_default():
    listed = {row["id"] for row in MultivendorOrchestrator.list_categories("lojadepaes")}
    assert listed == {"vinhos", "queijos", "frios", "azeites", "cervejas", "batatas"}
    assert "software" not in listed


def test_culinary_fallback_does_not_return_it_notebooks():
    from app.services.mercadolivre_fallback import get_fallback_offers

    titles = " ".join(item["title"] for item in get_fallback_offers("vinho tinto mesa"))
    assert "Vinho" in titles
    assert "Notebook" not in titles
