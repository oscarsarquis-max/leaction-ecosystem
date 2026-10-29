import json
import urllib.request

BASE = "http://127.0.0.1:4012/api/marketplace"


def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode())


def summarize(label, payload):
    shelves = payload.get("shelves") or []
    cats = [s.get("category") for s in shelves]
    offers = []
    for shelf in shelves:
        for offer in shelf.get("offers") or []:
            offers.append(
                {
                    "id": offer.get("id"),
                    "title": (offer.get("title") or "")[:80],
                    "link": offer.get("link"),
                    "fallback": offer.get("fallback"),
                    "category": offer.get("category") or shelf.get("category"),
                    "vendor": offer.get("vendor"),
                }
            )
    real = [
        o
        for o in offers
        if o["link"]
        and not str(o["id"]).startswith("fallback-")
        and o["fallback"] is not True
    ]
    print(label)
    print("  status", payload.get("status"), "origin", payload.get("origin"), "cats", cats)
    print("  offers", len(offers), "real", len(real))
    for item in real[:6]:
        print("   ", item["id"], item["category"], item["vendor"], item["title"])
        print("     ", item["link"])
    return real


status, legado = get("/vitrine?limit=4")
assert status == 200
legado_real = summarize("legado", legado)
assert legado.get("origin") in (None, "legado")
assert set(s.get("category") for s in (legado.get("shelves") or [])) <= {
    "formacao",
    "equipamentos",
    "software",
}

status, loja = get("/vitrine?limit=4", {"Accept": "application/json", "X-ActionHub-App-Id": "lojadepaes"})
assert status == 200
loja_real = summarize("loja_header", loja)
assert loja.get("origin") == "lojadepaes"
assert set(s.get("category") for s in (loja.get("shelves") or [])) <= {
    "vinhos",
    "queijos",
    "frios",
    "azeites",
}
assert "formacao" not in set(s.get("category") for s in (loja.get("shelves") or []))

status, query = get("/vitrine?limit=4&origin=lojadepaes")
assert status == 200
summarize("loja_query", query)
assert query.get("origin") == "lojadepaes"

status, unknown = get("/vitrine?limit=4", {"Accept": "application/json", "X-ActionHub-App-Id": "desconhecido"})
print("unknown", status, unknown.get("error"), unknown.get("offers"), unknown.get("shelves"))

print("PROBE_OK real_loja", len(loja_real), "real_legado", len(legado_real))
