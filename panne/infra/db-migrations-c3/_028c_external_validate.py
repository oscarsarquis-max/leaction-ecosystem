"""External validation CURSOR-028-C on demo. No secrets beyond public fake demo token."""
from __future__ import annotations

import json
import ssl
import uuid
import urllib.error
import urllib.request
from typing import Any

API = "https://api.demo.panne.ia.br"
FE = "https://demo.panne.ia.br"
TOKEN = "panne-demo:demo-owner"
CTX = ssl.create_default_context()


def req(method: str, path: str, *, org: str | None = None, body: dict | None = None, key: bool = False) -> tuple[int, Any]:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "X-Correlation-Id": str(uuid.uuid4()),
        "User-Agent": "028c-external/1",
    }
    if org:
        headers["X-Panne-Organization-Id"] = org
    if key:
        headers["Idempotency-Key"] = str(uuid.uuid4())
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=CTX, timeout=40) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw[:300]}
        return exc.code, parsed


def main() -> None:
    fails: list[str] = []
    created_products: list[str] = []
    created_families: list[str] = []

    # FE smoke
    with urllib.request.urlopen(FE + "/", context=CTX, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        assert "index-UnM8HMjM.js" in html or "produtos" in html.lower() or "assets/" in html
    print("fe_ok")

    code, me = req("GET", "/api/v1/me")
    print("me", code, "roles", [a.get("roles") for a in (me.get("associations") or me.get("data", {}).get("associations") or [])][:3])
    if code != 200:
        raise SystemExit(f"me failed {code} {me}")
    # tolerate shapes
    associations = me.get("associations") or (me.get("data") or {}).get("associations") or []
    if not associations:
        # some APIs nest under selected
        print("me_keys", list(me.keys()))
        raise SystemExit("no associations")
    org_a = str(associations[0]["organization_id"])
    org_b = str(associations[1]["organization_id"]) if len(associations) > 1 else None
    roles_a = associations[0].get("roles") or []
    print(f"org_a={org_a} roles={roles_a} org_b={org_b}")
    if "owner" not in roles_a and "organization_owner" not in roles_a:
        fails.append("owner_role")

    # summary + list
    code, summary = req("GET", f"/api/v1/organizations/{org_a}/products/summary", org=org_a)
    print("summary", code, summary)
    if code != 200:
        fails.append("summary")
    code, listed = req("GET", f"/api/v1/organizations/{org_a}/products", org=org_a)
    print("list", code, "total", listed.get("total"), "items", len(listed.get("items") or []))
    if code != 200 or int(listed.get("total") or 0) < 1:
        fails.append("list")
    else:
        first = listed["items"][0]
        detail_id = first["id"]
        code, detail = req("GET", f"/api/v1/organizations/{org_a}/products/{detail_id}", org=org_a)
        print("detail", code, detail.get("data", {}).get("display_name"), detail.get("data", {}).get("supply_mode"))
        if code != 200:
            fails.append("detail")
        # no cost leakage
        blob = json.dumps(detail)
        if "unit_cost" in blob or "cost_total" in blob:
            fails.append("cost_leak")

    # family
    code, fam = req(
        "POST",
        f"/api/v1/organizations/{org_a}/product-families",
        org=org_a,
        key=True,
        body={"code": "T028C-FAM", "display_name": "Família teste 028-C"},
    )
    print("family_create", code, fam.get("data", {}).get("code"))
    if code != 200:
        fails.append("family_create")
    else:
        created_families.append(fam["data"]["id"])
        fam_id = fam["data"]["id"]

    # purchased without recipe
    code, purchased = req(
        "POST",
        f"/api/v1/organizations/{org_a}/products",
        org=org_a,
        key=True,
        body={
            "code": "T028C-BUY",
            "display_name": "Produto comprado teste 028-C",
            "supply_mode": "purchased",
            "purpose": "final",
            "family_id": created_families[0] if created_families else None,
        },
    )
    print("purchased_create", code, purchased.get("data", {}).get("recipe_status_label"))
    if code != 200:
        fails.append("purchased_create")
    else:
        created_products.append(purchased["data"]["id"])
        if purchased["data"].get("recipe_status_label") != "Não se aplica":
            fails.append("purchased_label")

    # produced without recipe
    code, produced = req(
        "POST",
        f"/api/v1/organizations/{org_a}/products",
        org=org_a,
        key=True,
        body={
            "code": "T028C-MAKE",
            "display_name": "Produto produzido teste 028-C",
            "supply_mode": "produced",
            "purpose": "final",
        },
    )
    print("produced_create", code, produced.get("data", {}).get("recipe_status_label"))
    if code != 200:
        fails.append("produced_create")
    else:
        created_products.append(produced["data"]["id"])
        if produced["data"].get("recipe_status_label") != "Sem receita vigente":
            fails.append("produced_label")

    # edit purchased
    if created_products:
        pid = created_products[0]
        code, det = req("GET", f"/api/v1/organizations/{org_a}/products/{pid}", org=org_a)
        rv = det.get("row_version")
        headers_note = True
        # patch with If-Match via raw
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Panne-Organization-Id": org_a,
            "X-Correlation-Id": str(uuid.uuid4()),
            "Idempotency-Key": str(uuid.uuid4()),
            "If-Match": str(rv),
        }
        body = json.dumps({"display_name": "Produto comprado editado 028-C"}).encode()
        request = urllib.request.Request(
            f"{API}/api/v1/organizations/{org_a}/products/{pid}",
            data=body,
            headers=headers,
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(request, context=CTX, timeout=40) as resp:
                patched = json.loads(resp.read().decode())
                print("edit", resp.status, patched.get("data", {}).get("display_name"))
                if patched.get("data", {}).get("display_name") != "Produto comprado editado 028-C":
                    fails.append("edit")
        except urllib.error.HTTPError as exc:
            print("edit_fail", exc.code, exc.read()[:200])
            fails.append("edit")

    # operational blocks via production order create
    # need establishment from board/catalog
    code, board = req("GET", f"/api/v1/organizations/{org_a}/production/board", org=org_a)
    print("board", code, "keys", list(board.keys())[:8] if isinstance(board, dict) else type(board))
    if code != 200:
        fails.append("board")

    code, orders = req("GET", f"/api/v1/organizations/{org_a}/production/orders?limit=5", org=org_a)
    print("orders", code, "total", orders.get("total"), "items", len(orders.get("items") or []))
    if code != 200:
        fails.append("orders")

    # try create order for purchased — expect 422 human message
    code, catalog = req("GET", f"/api/v1/organizations/{org_a}/production/catalog", org=org_a)
    est_id = None
    if code == 200:
        establishments = catalog.get("establishments") or catalog.get("data", {}).get("establishments") or []
        if establishments:
            est_id = establishments[0].get("id")
        print("catalog_est", est_id)
    if est_id and len(created_products) >= 1:
        buy_id = created_products[0]
        code, blocked = req(
            "POST",
            f"/api/v1/organizations/{org_a}/production/orders",
            org=org_a,
            key=True,
            body={
                "establishment_id": est_id,
                "technical_product_id": buy_id,
                "target_mode": "mass",
                "target_quantity": "1000",
            },
        )
        msg = json.dumps(blocked, ensure_ascii=False)
        print("block_purchased", code, msg[:200])
        if code not in (400, 422) or "comprado" not in msg.lower():
            fails.append("block_purchased")

    if est_id and len(created_products) >= 2:
        make_id = created_products[1]
        code, blocked = req(
            "POST",
            f"/api/v1/organizations/{org_a}/production/orders",
            org=org_a,
            key=True,
            body={
                "establishment_id": est_id,
                "technical_product_id": make_id,
                "target_mode": "mass",
                "target_quantity": "1000",
            },
        )
        msg = json.dumps(blocked, ensure_ascii=False)
        print("block_produced", code, msg[:220])
        if code not in (400, 422) or "receita" not in msg.lower():
            fails.append("block_produced")

    # org switch
    if org_b:
        code, listed_b = req("GET", f"/api/v1/organizations/{org_b}/products", org=org_b)
        print("org_switch_list", code, "total", listed_b.get("total"))
        if code != 200:
            fails.append("org_switch")
        # cross-org isolation: purchased id must not appear in org_b
        if created_products:
            code, cross = req(
                "GET",
                f"/api/v1/organizations/{org_b}/products/{created_products[0]}",
                org=org_b,
            )
            print("cross_org", code)
            if code not in (403, 404):
                fails.append("cross_org")

    # cleanup test artifacts — inactivate products (no delete endpoint), inactivate family
    for pid in created_products:
        code, det = req("GET", f"/api/v1/organizations/{org_a}/products/{pid}", org=org_a)
        rv = det.get("row_version")
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Panne-Organization-Id": org_a,
            "X-Correlation-Id": str(uuid.uuid4()),
            "Idempotency-Key": str(uuid.uuid4()),
            "If-Match": str(rv),
        }
        body = json.dumps({"status": "inactive"}).encode()
        request = urllib.request.Request(
            f"{API}/api/v1/organizations/{org_a}/products/{pid}/status",
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, context=CTX, timeout=40) as resp:
                print("cleanup_product", pid[:8], resp.status)
        except urllib.error.HTTPError as exc:
            print("cleanup_product_fail", pid[:8], exc.code)
            fails.append("cleanup_product")

    for fid in created_families:
        code, rows = req("GET", f"/api/v1/organizations/{org_a}/product-families", org=org_a)
        row = next((r for r in (rows.get("items") or []) if r["id"] == fid), None)
        if not row:
            continue
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Panne-Organization-Id": org_a,
            "X-Correlation-Id": str(uuid.uuid4()),
            "Idempotency-Key": str(uuid.uuid4()),
            "If-Match": str(row["row_version"]),
        }
        body = json.dumps({"status": "inactive"}).encode()
        request = urllib.request.Request(
            f"{API}/api/v1/organizations/{org_a}/product-families/{fid}",
            data=body,
            headers=headers,
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(request, context=CTX, timeout=40) as resp:
                print("cleanup_family", fid[:8], resp.status)
        except urllib.error.HTTPError as exc:
            print("cleanup_family_fail", fid[:8], exc.code)
            fails.append("cleanup_family")

    # confirm canonical products remain
    code, listed_final = req("GET", f"/api/v1/organizations/{org_a}/products?status=active", org=org_a)
    print("active_after_cleanup", listed_final.get("total"))

    if fails:
        print("EXTERNAL_FAIL", fails)
        raise SystemExit(1)
    print("EXTERNAL_OK")


if __name__ == "__main__":
    main()
