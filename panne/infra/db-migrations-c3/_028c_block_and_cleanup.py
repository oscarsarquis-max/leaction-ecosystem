"""Use leftover T028C products or create unique ones; prove OP blocks; cleanup."""
from __future__ import annotations

import json
import ssl
import time
import uuid
import urllib.error
import urllib.request

API = "https://api.demo.panne.ia.br"
TOKEN = "panne-demo:demo-owner"
CTX = ssl.create_default_context()
ORG = "45104a8c-d590-5946-b8dd-f5534e89e338"
SUFFIX = time.strftime("%H%M%S")


def req(method, path, body=None, match=None):
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "X-Panne-Organization-Id": ORG,
        "X-Correlation-Id": str(uuid.uuid4()),
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
        h["Idempotency-Key"] = str(uuid.uuid4())
    if match is not None:
        h["If-Match"] = str(match)
    r = urllib.request.Request(API + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main() -> None:
    fails = []
    c, orders = req("GET", f"/api/v1/organizations/{ORG}/production/orders?limit=1")
    est = (orders.get("items") or [{}])[0].get("establishment_id")
    print("est", est)
    assert est

    c, buy = req(
        "POST",
        f"/api/v1/organizations/{ORG}/products",
        {
            "code": f"T028C-BUY-{SUFFIX}",
            "display_name": f"buy {SUFFIX}",
            "supply_mode": "purchased",
            "purpose": "final",
        },
    )
    c2, make = req(
        "POST",
        f"/api/v1/organizations/{ORG}/products",
        {
            "code": f"T028C-MAKE-{SUFFIX}",
            "display_name": f"make {SUFFIX}",
            "supply_mode": "produced",
            "purpose": "final",
        },
    )
    print("create", c, c2)
    assert c == 200 and c2 == 200

    for label, pid, expect in (
        ("block_buy", buy["data"]["id"], "comprado"),
        ("block_make", make["data"]["id"], "receita"),
    ):
        code, resp = req(
            "POST",
            f"/api/v1/organizations/{ORG}/production/orders",
            {
                "establishment_id": est,
                "technical_product_id": pid,
                "target_mode": "mass",
                "target_quantity": "1000",
            },
        )
        msg = json.dumps(resp, ensure_ascii=False)
        print(label, code, msg[:240])
        if code not in (400, 422) or expect not in msg.lower():
            fails.append(label)

    # cleanup all T028C products/families
    c, listed = req("GET", f"/api/v1/organizations/{ORG}/products?q=T028C")
    for item in listed.get("items") or []:
        if item.get("status") != "active":
            continue
        code, resp = req(
            "POST",
            f"/api/v1/organizations/{ORG}/products/{item['id']}/status",
            {"status": "inactive"},
            match=item["row_version"],
        )
        print("inact_product", item["code"], code)

    c, fams = req("GET", f"/api/v1/organizations/{ORG}/product-families")
    for fam in fams.get("items") or []:
        if not str(fam.get("code", "")).startswith("T028C"):
            continue
        if fam.get("status") != "active":
            continue
        code, resp = req(
            "PATCH",
            f"/api/v1/organizations/{ORG}/product-families/{fam['id']}",
            {"status": "inactive"},
            match=fam["row_version"],
        )
        print("inact_family", fam["code"], code)

    c, final = req("GET", f"/api/v1/organizations/{ORG}/products?status=active")
    print("active_total", final.get("total"))
    leftover = [i["code"] for i in (final.get("items") or []) if str(i.get("code", "")).startswith("T028C")]
    print("active_T028C", leftover)
    if leftover:
        fails.append("leftover")

    if fails:
        print("FAIL", fails)
        raise SystemExit(1)
    print("BLOCK_AND_CLEANUP_OK")


if __name__ == "__main__":
    main()
