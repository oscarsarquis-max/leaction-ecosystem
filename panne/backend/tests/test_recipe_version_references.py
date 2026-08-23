from uuid import uuid4

from app.modules.formula_lab.models import FormulationVersionRecipeReference
from sqlalchemy import select
from tests.test_production_api import _cleanup
from tests.test_recipe_http import _base, _create_recipe, _h, _publish_ingredient, _setup


def test_version_references_are_copied_and_identity_edit_does_not_rewrite_snapshot(engine):
    ctx = _setup(engine, "ref-ver")
    _publish_ingredient(ctx, "FAR-RV", "Farinha")
    created = _create_recipe(ctx, "PAO-RV", "Pão refs")
    recipe_id = created["data"]["id"]
    version_id = created["data"]["current_version"]["id"]
    ref = ctx["client"].post(
        _base(ctx, "/recipe-references"),
        headers=_h(ctx, key=uuid4()),
        json={"title": "Manual v1", "source_type": "internal", "notes": "original"},
    )
    assert ref.status_code == 200, ref.text
    identity = ctx["client"].get(_base(ctx, f"/recipes/{recipe_id}"), headers=_h(ctx)).json()
    linked = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/references"),
        headers=_h(ctx, match=identity["row_version"]),
        json={"recipe_reference_id": ref.json()["data"]["id"], "role": "source"},
    )
    assert linked.status_code == 200, linked.text
    version_refs = ctx["client"].get(
        _base(ctx, f"/recipes/{recipe_id}/versions/{version_id}/references"),
        headers=_h(ctx),
    )
    assert version_refs.status_code == 200
    assert version_refs.json()["data"]
    assert version_refs.json()["data"][0]["snapshot"]["title"] == "Manual v1"
    new_version = ctx["client"].post(
        _base(ctx, f"/recipes/{recipe_id}/versions"),
        headers=_h(ctx, key=uuid4()),
        json={"source_version_id": version_id},
    )
    assert new_version.status_code == 200
    copied = ctx["client"].get(
        _base(
            ctx,
            f"/recipes/{recipe_id}/versions/{new_version.json()['data']['id']}/references",
        ),
        headers=_h(ctx),
    )
    assert copied.json()["data"]
    assert copied.json()["data"][0]["snapshot"]["title"] == "Manual v1"
    session = ctx["admin"]
    row = session.scalars(
        select(FormulationVersionRecipeReference).where(
            FormulationVersionRecipeReference.formulation_version_id == version_id
        )
    ).first()
    assert row is not None
    _cleanup(ctx["client"])
    ctx["admin"].close()
