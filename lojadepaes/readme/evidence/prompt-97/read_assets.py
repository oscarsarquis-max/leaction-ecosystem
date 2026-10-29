from pathlib import Path
import json
import re
import urllib.request

OUT = Path(__file__).resolve().parent
html = urllib.request.urlopen(urllib.request.Request("https://lojadepaes.com.br/", headers={"User-Agent": "97"})).read().decode("utf-8", "replace")
report = {"assets": re.findall(r"/assets/[^\"']+", html)[:6]}
(OUT / "prod-assets.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(report)
