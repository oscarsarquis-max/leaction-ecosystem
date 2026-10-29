"""Upload Panne Demo FE (CURSOR-028 custos) to S3 + CloudFront invalidate only."""
from __future__ import annotations

import mimetypes
import time
from pathlib import Path

import boto3

REGION = "us-east-2"
BUCKET = "panne-demo-frontend-253137917703"
DIST_DIR = Path(r"C:\Projetos\_release-028\panne\frontend\dist")
DOMAIN = "demo.panne.ia.br"


def main() -> None:
    s3 = boto3.client("s3", region_name=REGION)
    cf = boto3.client("cloudfront")
    if not DIST_DIR.exists():
        raise SystemExit(f"dist missing: {DIST_DIR}")
    count = 0
    for path in DIST_DIR.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(DIST_DIR).as_posix()
        ctype = mimetypes.guess_type(key)[0] or "application/octet-type"
        if ctype == "application/octet-type":
            ctype = "application/octet-stream"
        cache = (
            "no-store, no-cache, must-revalidate, max-age=0, s-maxage=0"
            if key == "index.html" or key.endswith(".html")
            else "public,max-age=31536000,immutable"
        )
        s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": ctype, "CacheControl": cache})
        count += 1
        print(f"put {key}")
    print(f"uploaded={count}")
    dist_id = None
    for page in cf.get_paginator("list_distributions").paginate():
        for d in (page.get("DistributionList") or {}).get("Items") or []:
            aliases = (d.get("Aliases") or {}).get("Items") or []
            if DOMAIN in aliases:
                dist_id = d["Id"]
                break
        if dist_id:
            break
    if not dist_id:
        raise SystemExit("CloudFront distribution for demo.panne.ia.br not found")
    inv = cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "CallerReference": f"028-custos-{int(time.time())}",
            "Paths": {"Quantity": 1, "Items": ["/*"]},
        },
    )
    print("distribution", dist_id)
    print("invalidation", inv["Invalidation"]["Id"], inv["Invalidation"]["Status"])
    print("DEPLOY_FE_OK")


if __name__ == "__main__":
    main()
