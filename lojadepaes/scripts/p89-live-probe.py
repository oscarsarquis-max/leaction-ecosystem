import json
import re
import urllib.request

origin = "https://lojadepaes.com.br"
status = json.loads(urllib.request.urlopen(f"{origin}/api/v1/gigio/status", timeout=20).read())
html = urllib.request.urlopen(f"{origin}/", timeout=20).read().decode("utf-8", "replace")
assets = re.findall(r"/assets/[^\"']+", html)
print(json.dumps({"status": status, "assets": assets[:8]}, ensure_ascii=False, indent=2))
