import json
import urllib.request

req = urllib.request.Request(
    "https://metodologiasinovativas.com.br/api/admin/login",
    data=json.dumps({"password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    print(resp.status, resp.read().decode())
