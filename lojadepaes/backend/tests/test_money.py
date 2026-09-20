import pytest
from app.domain.errors import ProductError
from app.domain.money import cents_to_brl, parse_brl_to_cents, slugify


def test_parse_brl_24_90() -> None:
    assert parse_brl_to_cents("24,90") == 2490
    assert parse_brl_to_cents("1.240,50") == 124050
    assert parse_brl_to_cents(" 25 ") == 2500
    assert parse_brl_to_cents("") is None
    assert parse_brl_to_cents(None) is None


def test_parse_brl_rejects_invalid() -> None:
    with pytest.raises(ProductError):
        parse_brl_to_cents("24.90")
    with pytest.raises(ProductError):
        parse_brl_to_cents("0,00")
    with pytest.raises(ProductError):
        parse_brl_to_cents(0)


def test_cents_format_and_slug() -> None:
    assert cents_to_brl(2490) == "24,90"
    assert cents_to_brl(124050) == "1.240,50"
    assert slugify("Pão de Fermentação") == "pao-de-fermentacao"
