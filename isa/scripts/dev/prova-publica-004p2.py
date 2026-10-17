"""Prova no site publicado. As senhas entram só pelo ambiente e não são impressas."""

import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "prototype" / "fixtures" / "bb-extrato-sintetico.csv"
SHOTS = ROOT / "documents" / "reviews" / "publicacao-004p2"
SITE = "https://isa.actionhub.com.br/"


def login(page, email, password):
    def watch(response):
        path = response.url.split("?")[0].replace("https://isa.actionhub.com.br", "")
        if "/callback" in path or "/api/" in path:
            names = []
            for header in response.headers_array():
                if header["name"].lower() == "set-cookie":
                    names.append(header["value"].split("=", 1)[0])
            print("RESP", response.status, path, ",".join(names))
    page.on("response", watch)
    page.goto(SITE, wait_until="networkidle")
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_url("**amazoncognito.com**", timeout=30000)
    page.locator("#signInFormUsername").locator("visible=true").fill(email)
    page.locator("#signInFormPassword").locator("visible=true").fill(password)
    page.locator("input[name='signInSubmitButton']").locator("visible=true").click()
    page.wait_for_function("() => location.hostname === 'isa.actionhub.com.br'", timeout=30000)
    try:
        page.wait_for_selector("text=Importar extrato", timeout=20000)
    except Exception:
        text = page.inner_text("body")[:400]
        text = __import__("re").sub(r"[\w.+-]+@[\w.-]+", "[email]", text)
        print("URL", page.url.split("?")[0])
        print(text)
        raise


def main():
    email = os.environ["ISA_PROVA_EMAIL"]
    password = os.environ["ISA_PROVA_PASSWORD"]
    email_two = os.environ["ISA_PROVA_EMAIL_2"]
    password_two = os.environ["ISA_PROVA_PASSWORD_2"]
    SHOTS.mkdir(parents=True, exist_ok=True)
    sample = SHOTS / "extrato-bb.csv"
    shutil.copyfile(FIXTURE, sample)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(SITE, wait_until="networkidle")
        body = page.inner_text("body")
        for banned in ("Marina", "Paulo", "Eveline", "Entrar como"):
            if banned in body:
                raise SystemExit("a entrada publicada mostrou identidade de demonstração")
        if "Entrar" not in body:
            raise SystemExit("o botão Entrar não apareceu")
        page.screenshot(path=str(SHOTS / "entrada-390.png"), full_page=True)
        login(page, email, password)
        page.screenshot(path=str(SHOTS / "vazia-390.png"), full_page=True)
        if "Pix recebido" in page.inner_text("body"):
            raise SystemExit("a conta nova já tinha lançamento")
        page.get_by_role("button", name="Importar extrato").first.click()
        page.set_input_files("#statement-file", str(sample))
        page.wait_for_selector("#import-go", timeout=20000)
        page.screenshot(path=str(SHOTS / "previa-390.png"), full_page=True)
        page.click("#import-go")
        page.wait_for_selector("text=Entraram", timeout=20000)
        if "Pix recebido" not in page.inner_text("body"):
            raise SystemExit("a importação não apareceu depois de gravar")
        page.screenshot(path=str(SHOTS / "importado-390.png"), full_page=True)
        flags = []
        for item in context.cookies():
            if item["name"] == "isa_session":
                flags.append("secure=%s httponly=%s samesite=%s domain=%s" % (item.get("secure"), item.get("httpOnly"), item.get("sameSite"), item.get("domain") or ""))
        page.goto(SITE + "#planejar", wait_until="networkidle")
        page.wait_for_selector("text=disponível", timeout=15000)
        page.screenshot(path=str(SHOTS / "planejar-390.png"), full_page=True)
        page.click("#nav-perfil")
        page.click("#leave")
        page.wait_for_selector("text=Entrar", timeout=15000)
        context.close()
        wide = browser.new_context(viewport={"width": 1280, "height": 800})
        again = wide.new_page()
        login(again, email, password)
        again.wait_for_selector("text=Pix recebido", timeout=20000)
        again.screenshot(path=str(SHOTS / "recuperado-1280.png"), full_page=True)
        again.click("#nav-perfil")
        again.click("#leave")
        again.wait_for_selector("text=Entrar", timeout=15000)
        wide.close()
        other = browser.new_context(viewport={"width": 1280, "height": 800})
        second = other.new_page()
        login(second, email_two, password_two)
        second.wait_for_timeout(1000)
        if "Pix recebido" in second.inner_text("body"):
            raise SystemExit("a segunda pessoa viu o lançamento da primeira")
        second.screenshot(path=str(SHOTS / "outra-pessoa-1280.png"), full_page=True)
        other.close()
        browser.close()
    sample.unlink(missing_ok=True)
    if not flags:
        raise SystemExit("a sessão não ficou no cookie")
    print("prova publicada ok")
    print(flags[0])


if __name__ == "__main__":
    sys.exit(main() or 0)
