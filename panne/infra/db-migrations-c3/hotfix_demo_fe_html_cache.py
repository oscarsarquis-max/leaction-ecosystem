"""Point Demo CloudFront HTML to CachingDisabled; keep hashed /assets/* immutable."""
from __future__ import annotations

import boto3

DIST = "E3F15FWBZ6P36W"
REGION = "us-east-2"
CACHING_DISABLED = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
CACHING_OPTIMIZED = "658327ea-f89d-4fab-a63d-7e88639e58f6"


def main() -> None:
    cf = boto3.client("cloudfront")
    raw = cf.get_distribution_config(Id=DIST)
    etag = raw["ETag"]
    cfg = raw["DistributionConfig"]
    default = cfg["DefaultCacheBehavior"]
    default["CachePolicyId"] = CACHING_DISABLED
    behaviors = cfg.get("CacheBehaviors") or {"Quantity": 0, "Items": []}
    items = list(behaviors.get("Items") or [])
    if not any(item.get("PathPattern") == "/assets/*" for item in items):
        items.insert(
            0,
            {
                "PathPattern": "/assets/*",
                "TargetOriginId": default["TargetOriginId"],
                "ViewerProtocolPolicy": default["ViewerProtocolPolicy"],
                "AllowedMethods": default["AllowedMethods"],
                "SmoothStreaming": False,
                "Compress": True,
                "LambdaFunctionAssociations": {"Quantity": 0},
                "FunctionAssociations": {"Quantity": 0},
                "FieldLevelEncryptionId": "",
                "CachePolicyId": CACHING_OPTIMIZED,
                "OriginRequestPolicyId": default.get("OriginRequestPolicyId") or "",
                "TrustedSigners": {"Enabled": False, "Quantity": 0},
                "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
                "GrpcConfig": {"Enabled": False},
            },
        )
    cfg["CacheBehaviors"] = {"Quantity": len(items), "Items": items}
    cf.update_distribution(Id=DIST, IfMatch=etag, DistributionConfig=cfg)
    print("default_cache", CACHING_DISABLED)
    print("assets_cache", CACHING_OPTIMIZED)
    print("behaviors", [i.get("PathPattern") for i in items])
    print("CF_CACHE_HTML_DISABLED_OK")


if __name__ == "__main__":
    main()
