"""Deploy demo FE to S3+CloudFront; proxy API same-origin. img7b API already on ALB."""
from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path

import boto3

ACCOUNT = "253137917703"
REGION = "us-east-2"
BUCKET = "panne-demo-frontend-253137917703"
DIST_DIR = Path(r"c:\Projetos\panne\frontend\dist")
ZONE = "Z0036120YQCHVOKHX8H7"
CERT_CF = "arn:aws:acm:us-east-1:253137917703:certificate/70b100cc-f5da-44c1-bae1-191e0f4e02fe"
ALB_DNS = "api.demo.panne.ia.br"
DOMAIN = "demo.panne.ia.br"


def main() -> None:
    s3 = boto3.client("s3", region_name=REGION)
    cf = boto3.client("cloudfront")
    r53 = boto3.client("route53")

    # bucket
    try:
        s3.head_bucket(Bucket=BUCKET)
        print("bucket_exists")
    except Exception:
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        print("bucket_created")
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_ownership_controls(
        Bucket=BUCKET,
        OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
    )

    # upload dist
    if not DIST_DIR.exists():
        raise SystemExit("dist missing")
    count = 0
    for path in DIST_DIR.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(DIST_DIR).as_posix()
        ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
        cache = "no-cache" if key == "index.html" else "public,max-age=31536000,immutable"
        s3.upload_file(
            str(path),
            BUCKET,
            key,
            ExtraArgs={"ContentType": ctype, "CacheControl": cache},
        )
        count += 1
    print(f"uploaded={count}")

    # OAC
    oac_id = None
    for item in cf.list_origin_access_controls().get("OriginAccessControlList", {}).get("Items", []) or []:
        if item.get("Name") == "panne-demo-fe-oac":
            oac_id = item["Id"]
            break
    if not oac_id:
        oac = cf.create_origin_access_control(
            OriginAccessControlConfig={
                "Name": "panne-demo-fe-oac",
                "Description": "Panne demo FE OAC",
                "SigningProtocol": "sigv4",
                "SigningBehavior": "always",
                "OriginAccessControlOriginType": "s3",
            }
        )
        oac_id = oac["OriginAccessControl"]["Id"]
    print("oac", oac_id)

    # existing distribution?
    dist_id = None
    domain_name = None
    for page in cf.get_paginator("list_distributions").paginate():
        for d in (page.get("DistributionList") or {}).get("Items") or []:
            aliases = (d.get("Aliases") or {}).get("Items") or []
            if DOMAIN in aliases:
                dist_id = d["Id"]
                domain_name = d["DomainName"]
                break
        if dist_id:
            break

    s3_origin = f"{BUCKET}.s3.{REGION}.amazonaws.com"
    if not dist_id:
        cfg = {
            "CallerReference": f"panne-demo-{int(time.time())}",
            "Aliases": {"Quantity": 1, "Items": [DOMAIN]},
            "DefaultRootObject": "index.html",
            "Origins": {
                "Quantity": 2,
                "Items": [
                    {
                        "Id": "s3-fe",
                        "DomainName": s3_origin,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "OriginAccessControlId": oac_id,
                    },
                    {
                        "Id": "alb-api",
                        "DomainName": ALB_DNS,
                        "CustomOriginConfig": {
                            "HTTPPort": 80,
                            "HTTPSPort": 443,
                            "OriginProtocolPolicy": "https-only",
                            "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                        },
                    },
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "s3-fe",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                },
                "Compress": True,
                "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",  # CachingOptimized
                "OriginRequestPolicyId": "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf",  # CORS-S3Origin
            },
            "CacheBehaviors": {
                "Quantity": 4,
                "Items": [
                    _api_behavior("/api/*"),
                    _api_behavior("/health"),
                    _api_behavior("/ready"),
                    _api_behavior("/openapi.json"),
                ],
            },
            "CustomErrorResponses": {
                "Quantity": 2,
                "Items": [
                    {
                        "ErrorCode": 403,
                        "ResponsePagePath": "/index.html",
                        "ResponseCode": "200",
                        "ErrorCachingMinTTL": 0,
                    },
                    {
                        "ErrorCode": 404,
                        "ResponsePagePath": "/index.html",
                        "ResponseCode": "200",
                        "ErrorCachingMinTTL": 0,
                    },
                ],
            },
            "Comment": "panne demo FE",
            "Enabled": True,
            "ViewerCertificate": {
                "ACMCertificateArn": CERT_CF,
                "SSLSupportMethod": "sni-only",
                "MinimumProtocolVersion": "TLSv1.2_2021",
            },
            "HttpVersion": "http2",
            "PriceClass": "PriceClass_100",
        }
        created = cf.create_distribution(DistributionConfig=cfg)
        dist_id = created["Distribution"]["Id"]
        domain_name = created["Distribution"]["DomainName"]
        print("cf_created", dist_id, domain_name)
    else:
        print("cf_exists", dist_id, domain_name)
        # invalidate
        cf.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                "CallerReference": f"inv-{int(time.time())}",
                "Paths": {"Quantity": 1, "Items": ["/*"]},
            },
        )
        print("invalidated")

    # bucket policy for OAC
    acct = ACCOUNT
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontOAC",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{BUCKET}/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{acct}:distribution/{dist_id}"
                    }
                },
            }
        ],
    }
    s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(policy))
    print("bucket_policy_ok")

    # DNS alias to CloudFront
    # CloudFront hosted zone id is global Z2FDTNDATAQYW2
    r53.change_resource_record_sets(
        HostedZoneId=ZONE,
        ChangeBatch={
            "Comment": "demo.panne.ia.br -> CloudFront",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": f"{DOMAIN}.",
                        "Type": "A",
                        "AliasTarget": {
                            "HostedZoneId": "Z2FDTNDATAQYW2",
                            "DNSName": domain_name,
                            "EvaluateTargetHealth": False,
                        },
                    },
                }
            ],
        },
    )
    print("dns_demo_ok", domain_name)
    Path(r"c:\Projetos\panne\documentacao\infraestrutura\_homolog-demo-cf.json").write_text(
        json.dumps(
            {
                "bucket": BUCKET,
                "distribution_id": dist_id,
                "cloudfront_domain": domain_name,
                "api_image": "backend-027-homolog-seed-142b356-img7b",
                "api_digest": "sha256:01c691ebd21fae0dbaf64c5cf2fad35e49bd2fa49f433d60f4be8a329abc0236",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _api_behavior(path: str) -> dict:
    return {
        "PathPattern": path,
        "TargetOriginId": "alb-api",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 7,
            "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
            "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
        },
        "Compress": True,
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # CachingDisabled
        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",  # AllViewerExceptHostHeader
    }


if __name__ == "__main__":
    main()
