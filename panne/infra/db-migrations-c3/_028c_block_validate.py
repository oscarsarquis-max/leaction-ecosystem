"""Block OP checks + cleanup ephemeral products."""
from __future__ import annotations

import json
import ssl
import uuid
import urllib.error
import urllib.request

API = "https://api.demo.panne.ia.br"
TOKEN = "panne-demo:demo-owner"
CTX = ssl.create_default_context()
ORG = "45104a8c-d590-5946-b8dd-f5534e89e338"


def req(method, path, body=None):
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
    r = urllib.request.Request(API + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def inactivate_product(pid: str) -> None:
    c, d = req("GET", f"/api/v1/organizations/{ORG}/products/{pid}")
    rv = d.get("row_version")
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "X-Panne-Organization-Id": ORG,
        "X-Correlation-Id": str(uuid.uuid4()),
        "Idempotency-Key": str(uuid.uuid4()),
        "If-Match": str(rv),
    }
    r = urllib.request.Request(
        API + f"/api/v1/organizations/{ORG}/products/{pid}/status",
        data=json.dumps({"status": "inactive"}).encode(),
        headers=h,
        method="POST",
    )
    with urllib.request.urlopen(r, context=CTX, timeout=40) as resp:
        print("cleanup_product", pid[:8], resp.status)


def main() -> None:
    fails = []
    c, fam = req(
        "POST",
        f"/api/v1/organizations/{ORG}/product-families",
        {"code": "T028C-FAM2", "display_name": "tmp"},
    )
    print("fam", c)
    c, buy = req(
        "POST",
        f"/api/v1/organizations/{ORG}/products",
        {
            "code": "T028C-BUY2",
            "display_name": "buy2",
            "supply_mode": "purchased",
            "purpose": "final",
        },
    )
    c2, make = req(
        "POST",
        f"/api/v1/organizations/{ORG}/products",
        {
            "code": "T028C-MAKE2",
            "display_name": "make2",
            "supply_mode": "produced",
            "purpose": "final",
        },
    )
    print("create", c, c2)

    c, orders = req("GET", f"/api/v1/organizations/{ORG}/production/orders?limit=1")
    item = (orders.get("items") or [None])[0]
    est = None
    if item:
        est = item.get("establishment_id") or (item.get("establishment") or {}).get("id")
        print("order_sample_keys", list(item.keys())[:25])
    c, board = req("GET", f"/api/v1/organizations/{ORG}/production/board")
    data = board.get("data") or board
    if isinstance(data, dict):
        print("board_keys", list(data.keys())[:30])
        if not est:
            est = (
                data.get("establishment_id")
                or (data.get("establishment") or {}).get("id")
                or (data.get("context") or {}).get("establishment_id")
            )
    else:
        print("board_data_type", type(data).__name__)
    c, cat = req("GET", f"/api/v1/organizations/{ORG}/production/catalog")
    print("catalog_top", list(cat.keys()) if isinstance(cat, dict) else type(cat), str(cat)[:250])
    if not est and isinstance(cat, dict):
        for key in ("establishments", "items"):
            rows = cat.get(key) or (cat.get("data") or {}).get(key) or []
            if rows and isinstance(rows, list):
                est = rows[0].get("id") or rows[0].get("establishment_id")
                break
    if not est and isinstance(data, dict):
        for card in data.get("orders") or data.get("items") or []:
            est = card.get("establishment_id") or (card.get("establishment") or {}).get("id")
            if est:
                break
    print("est", est)

    def try_order(pid, label, expect):
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

    if est and buy.get("data"):
        try_order(buy["data"]["id"], "block_buy", "comprado")
    else:
        fails.append("no_est_or_buy")
    if est and make.get("data"):
        try_order(make["data"]["id"], "block_make", "receita")
    else:
        fails.append("no_est_or_make")

    for p in (buy, make):
        if p.get("data"):
            inactivate_product(p["data"]["id"])
    if fam.get("data"):
        fid = fam["data"]["id"]
        c, rows = req("GET", f"/api/v1/organizations/{ORG}/product-families")
        row = next((x for x in rows.get("items") or [] if x["id"] == fid), None)
        if row:
            h = {
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
                "X-Panne-Organization-Id": ORG,
                "X-Correlation-Id": str(uuid.uuid4()),
                "Idempotency-Key": str(uuid.uuid4()),
                "If-Match": str(row["row_version"]),
            }
            r = urllib.request.Request(
                API + f"/api/v1/organizations/{ORG}/product-families/{fid}",
                data=json.dumps({"status": "inactive"}).encode(),
                headers=h,
                method="PATCH",
            )
            with urllib.request.urlopen(r, context=CTX, timeout=40) as resp:
                print("cleanup_fam", resp.status)

    if fails:
        print("BLOCK_FAIL", fails)
        raise SystemExit(1)
    print("BLOCK_OK")


if __name__ == "__main__":
    main()
