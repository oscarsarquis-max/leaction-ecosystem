"""Amazon S3 adapter — private dedicated bucket, us-east-2 (ADR-007)."""

from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import Settings
from app.storage.base import ObjectHead, PresignedUpload


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        self._bucket = settings.s3_bucket
        # Regional endpoint avoids TemporaryRedirect (307) on presigned PUT/GET
        # when the default global host s3.amazonaws.com is used for non-us-east-1.
        endpoint = settings.s3_endpoint_url or f"https://s3.{settings.s3_region}.amazonaws.com"
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            endpoint_url=endpoint,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    def generate_key(self, organization_id: str, evidence_id: str, version_no: int = 1) -> str:
        return f"org/{organization_id}/evidence/{evidence_id}/v{version_no}"

    def generate_report_pdf_key(
        self, organization_id: str, report_id: str, version_no: int
    ) -> str:
        return f"org/{organization_id}/reports/{report_id}/v{version_no}.pdf"

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def presign_upload(
        self,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        expires_in: int,
    ) -> PresignedUpload:
        # Presigned PUT binds Bucket + Key + ContentType + expiry (SigV4).
        # Size is enforced on receive via HEAD/get (PUT Content-Length is not a
        # reliable signed constraint for all clients); max_bytes is documented
        # in the authorize response contract and checked server-side.
        _ = max_bytes
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return PresignedUpload(
            url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            expires_in_seconds=expires_in,
        )

    def presign_download(self, key: str, *, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )

    def head(self, key: str) -> ObjectHead:
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=key)
        except self._client.exceptions.NoSuchKey:  # type: ignore[attr-defined]
            return ObjectHead(exists=False)
        except Exception as exc:
            # botocore ClientError 404
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return ObjectHead(exists=False)
            raise
        return ObjectHead(
            exists=True,
            content_length=int(resp.get("ContentLength") or 0),
            content_type=resp.get("ContentType"),
            etag=resp.get("ETag"),
        )

    def get_bytes(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
