from collections.abc import Iterator

import pytest

pytestmark = pytest.mark.contract


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "contract: contrato atual de pedidos, avisos e catálogo")


@pytest.fixture(autouse=True)
def _contract_payments_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A cobrança automática no aceite depende da flag. O eixo de pagamento liga o checkout à parte."""
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
