"""Read-only check of the authorized order page. Does not start Pix or card."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

EVIDENCE = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-71"


def main() -> int:
    href = os.environ.get("P71_ORDER_HREF", "").strip()
    if not href or "token=" not in href:
        print("missing authorized href", file=sys.stderr)
        return 2
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = context.new_page()
        page.set_default_timeout(25000)
        page.goto(href)
        page.get_by_role("button", name="Pagar com Pix").wait_for()
        page.get_by_role("button", name="Pagar com cartão").wait_for()
        pix = page.get_by_role("button", name="Pagar com Pix")
        card = page.get_by_role("button", name="Pagar com cartão")
        assert pix.is_enabled()
        assert card.is_enabled()
        page.screenshot(path=EVIDENCE / "prod-pay-actions-390.png", full_page=True)
        context.close()
        browser.close()
    (EVIDENCE / "prod-read.json").write_text(
        json.dumps(
            {
                "path": "/pedido/LP42BF063F0C",
                "pix_visible": True,
                "card_visible": True,
                "clicked_provider": False,
                "viewport": 390,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("prod read: pix+card visible, no provider click")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
