import mimetypes
import time
import urllib.request
import ssl
from pathlib import Path

import boto3

BUCKET = "panne-demo-frontend-253137917703"
DIST = Path(r"c:\Projetos\panne\frontend\dist")
BUNDLE = "index-UW3USK9F.js"

s3 = boto3.client("s3", region_name="us-east-2")
n = 0
for path in DIST.rglob("*"):
    if not path.is_file():
        continue
    key = path.relative_to(DIST).as_posix()
    ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
    cache = "no-cache" if key == "index.html" else "public,max-age=31536000,immutable"
    s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": ctype, "CacheControl": cache})
    n += 1
print("uploaded", n)

cf = boto3.client("cloudfront")
inv = cf.create_invalidation(
    DistributionId="E3F15FWBZ6P36W",
    InvalidationBatch={
        "CallerReference": f"user-menu-{int(time.time())}",
        "Paths": {"Quantity": 1, "Items": ["/*"]},
    },
)
print("invalidation", inv["Invalidation"]["Id"])
print("bundle", BUNDLE)

ctx = ssl.create_default_context()
for _ in range(15):
    html = urllib.request.urlopen(
        f"https://demo.panne.ia.br/?t={time.time()}", context=ctx, timeout=30
    ).read().decode()
    if BUNDLE in html:
        print("external_ok", BUNDLE)
        break
    time.sleep(4)
else:
    print("pending")
