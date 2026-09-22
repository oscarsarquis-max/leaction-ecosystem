import pytest

from app.modules.costing_pricing.presentation import canonical_supply_mode, cost_scope_report


def test_name_suffix_inference_is_gone() -> None:
    with pytest.raises(ImportError):
        from app.modules.costing_pricing.presentation import infer_supply_mode  # noqa: F401


def test_canonical_modes_stay_and_absence_does_not_classify() -> None:
    assert canonical_supply_mode("purchased") == "purchased"
    assert canonical_supply_mode("produced") == "produced"
    assert canonical_supply_mode(None) is None
    assert canonical_supply_mode("") is None
    assert canonical_supply_mode("comprado") is None
    assert canonical_supply_mode("MANTEIGA-PT") is None


def test_scope_uses_only_canonical_mode() -> None:
    butter_name = {
        "category": "ingredient",
        "amount": "18.00",
        "price_missing": False,
        "display_name": "Manteiga comprada",
    }
    purchased = cost_scope_report(
        [butter_name], policy=None, completeness="complete", supply_mode="purchased"
    )
    produced = cost_scope_report(
        [butter_name], policy=None, completeness="complete", supply_mode="produced"
    )
    missing = cost_scope_report(
        [butter_name], policy=None, completeness="complete", supply_mode=None
    )
    assert purchased["mode"] == "purchased"
    assert purchased["comparison_scope_label"] == "Mercadoria comprada"
    assert produced["mode"] == "produced"
    assert produced["comparison_scope_label"] != "Mercadoria comprada"
    assert missing["mode"] is None
    assert missing["comparison_scope_label"] == "Modalidade não informada"
