import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:4012/api/marketplace/vitrine?limit=6",
    headers={"Accept": "application/json", "X-ActionHub-App-Id": "lojadepaes"},
)
with urllib.request.urlopen(req, timeout=25) as response:
    data = json.loads(response.read().decode())
print("origin", data.get("origin"))
for shelf in data.get("shelves") or []:
    print("SHELF", shelf.get("category"), "count", shelf.get("count"), "source", shelf.get("source"))
    for offer in shelf.get("offers") or []:
        title = (offer.get("title") or "")[:100]
        print(" ", offer.get("id"), "fallback", offer.get("fallback"), title)
        print("   ", offer.get("link"))
