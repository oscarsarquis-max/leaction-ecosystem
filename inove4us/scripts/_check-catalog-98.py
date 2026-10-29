import json
import requests

r = requests.get("https://actionhub.com.br/hub-api/v1/catalog/inove4us-school", timeout=20)
plans = r.json().get("plans") or []
out = []
for p in plans:
    out.append(
        {
            "sku": p.get("sku"),
            "credits": p.get("credits"),
            "licenses": p.get("licenses_granted"),
            "ia_feat": [f for f in (p.get("features") or []) if "IA" in f],
        }
    )
print(json.dumps(out, ensure_ascii=False, indent=2))
