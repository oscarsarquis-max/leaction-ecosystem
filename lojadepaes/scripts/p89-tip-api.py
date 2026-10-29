import json
import urllib.request

ORIGIN = "https://lojadepaes.com.br"
catalog = json.loads(urllib.request.urlopen(f"{ORIGIN}/api/v1/catalog/bread-builder", timeout=30).read())
flour = next(r for r in catalog["flours"] if r.get("slug") == "farinha-branca-strong-white")
dough = next(r for r in catalog["doughs"] if r.get("slug") == "fermentacao-natural-curta")
shape = next(r for r in catalog["shapes"] if r.get("slug") == "pao-de-forma")
nuts = next((r for r in catalog["ingredients"] if r.get("slug") == "nozes"), None)
body = {
    "flour_id": flour["id"],
    "dough_id": dough["id"],
    "ingredient_ids": [nuts["id"]] if nuts else [],
    "shape_id": shape["id"],
    "free_text": "",
    "occasion": "verificação do criador",
}
req = urllib.request.Request(
    f"{ORIGIN}/api/v1/gigio/builder-tip",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=90) as resp:
    tip = json.loads(resp.read())
print(json.dumps({
    "ok": tip.get("ok"),
    "flour": (tip.get("composition") or {}).get("flour"),
    "prep": (tip.get("composition") or {}).get("preparation"),
    "incl": (tip.get("composition") or {}).get("inclusions"),
    "shape": (tip.get("composition") or {}).get("shape"),
    "obs": str(tip.get("observation") or "")[:180],
}, ensure_ascii=False))
