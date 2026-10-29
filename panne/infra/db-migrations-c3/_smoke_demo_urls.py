import time
import urllib.request
import ssl
import boto3

ctx = ssl.create_default_context()
for host, path in [
    ("api.demo.panne.ia.br", "/api/v1/public/login-editorial"),
    ("demo.panne.ia.br", "/api/v1/public/login-editorial"),
    ("demo.panne.ia.br", "/api/v1/me"),
    ("demo.panne.ia.br", "/health"),
]:
    url = f"https://{host}{path}"
    try:
        r = urllib.request.urlopen(url, context=ctx, timeout=25)
        print(host, path, r.status, r.headers.get("content-type"), r.read(100))
    except Exception as e:
        body = e.read()[:120] if hasattr(e, "read") else b""
        print(host, path, "HTTP", getattr(e, "code", e), body)

cf = boto3.client("cloudfront")
cf.create_invalidation(
    DistributionId="E3F15FWBZ6P36W",
    InvalidationBatch={
        "CallerReference": str(time.time()),
        "Paths": {"Quantity": 1, "Items": ["/*"]},
    },
)
print("invalidation_started")
