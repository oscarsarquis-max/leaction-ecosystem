"""Jornada visual do primeiro acesso contra a API local. Não é coletado pelo pytest."""

from uuid import uuid4

from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import postgres_url
from app.modules.identity_organization.onboarding import issue_onboarding_authorization

BASE = "http://127.0.0.1:5181"
EMAIL = "gate-onboarding@example.invalid"
FORBIDDEN = ("subject", "issuer", "payload", "backend", "órfã", "Acesso negado")


def _overflow(page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


def _visible_text(page) -> str:
    return page.locator("body").inner_text()


def _grant() -> None:
    engine = create_engine(postgres_url(), future=True)
    session = sessionmaker(bind=engine, future=True)()
    try:
        issue_onboarding_authorization(
            session, email=EMAIL, commercial_condition="complimentary"
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()


def main() -> None:
    token = uuid4().hex[:8]
    trade = f"Operacao {token}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{BASE}/entrar")
        page.get_by_role("heading", name="Entrar na Panne").wait_for()
        brand = page.locator("img.login-center__brand")
        assert brand.count() == 1
        assert brand.get_attribute("alt") == "Panne"
        page.get_by_role("button", name="Entrar em desenvolvimento").click()
        page.get_by_role("heading", name="Primeiro acesso").wait_for()
        blocked = _visible_text(page)
        assert "não tem autorização da Panne" in blocked
        assert "Sair" in blocked
        assert "suporte da Panne" in blocked
        for word in FORBIDDEN:
            assert word not in blocked
        assert _overflow(page)
        page.keyboard.press("Tab")
        assert page.evaluate("() => document.activeElement !== document.body")

        _grant()
        page.reload()
        page.get_by_label("Nome comercial").wait_for()
        assert "Acesso sem cobrança da Panne nesta etapa" in _visible_text(page)
        assert page.get_by_label("Razão social").count() == 0
        page.get_by_label("Pessoa jurídica").check()
        page.get_by_label("Razão social").wait_for()
        page.get_by_label("CNPJ").wait_for()
        page.get_by_label("Pessoa física").check()
        assert page.get_by_label("Razão social").count() == 0
        page.get_by_label("Ainda sem empresa formalizada").check()

        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_label("Nome comercial").fill(trade)
        page.get_by_label("Nome do titular").fill("Titular de teste")
        page.get_by_label("CPF do titular").fill("39053344705")
        page.get_by_label("Nome do estabelecimento").fill("Estabelecimento de teste")
        page.get_by_label("Aceito a condição comercial apresentada").check()
        assert _overflow(page)
        page.get_by_role("button", name="Cadastrar cliente").click()
        page.get_by_text(f"{trade} está ativo").wait_for()
        done = _visible_text(page)
        assert f"{trade} está ativo" in done
        assert "Estabelecimento de teste" in done
        assert "39053344705" not in done
        for word in FORBIDDEN:
            assert word not in done
        assert _overflow(page)

        page.set_viewport_size({"width": 1280, "height": 800})
        page.get_by_role("button", name="Abrir menu do usuário").click()
        page.get_by_role("menuitem", name="Sair").click()
        page.get_by_role("heading", name="Entrar na Panne").wait_for()
        page.get_by_role("button", name="Entrar em desenvolvimento").click()
        page.get_by_role("button", name="Abrir menu do usuário").wait_for()
        again = _visible_text(page)
        assert "Primeiro acesso" not in again
        assert "não tem autorização da Panne" not in again
        assert _overflow(page)
        browser.close()
    print("browser-gate-ok")


if __name__ == "__main__":
    main()
