"""S3 integration — skipped unless QMIND_S3_INTEGRATION=1 and real bucket configured."""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("QMIND_S3_INTEGRATION") != "1",
    reason="Set QMIND_S3_INTEGRATION=1 with S3_BUCKET credentials to run",
)
def test_s3_presign_put_head_get_delete():
    from app.config import Settings
    from app.storage.s3 import S3ObjectStorage

    settings = Settings(
        database_url_admin=os.environ["DATABASE_URL_ADMIN"],
        database_url_app=os.environ["DATABASE_URL_APP"],
        storage_backend="s3",
        s3_bucket=os.environ["S3_BUCKET"],
        s3_region=os.environ.get("S3_REGION", "us-east-2"),
        s3_endpoint_url=os.environ.get("S3_ENDPOINT_URL", ""),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        allow_simulated_security_pass=True,
        environment="local",
        auth_mode="dev",
    )
    store = S3ObjectStorage(settings)
    key = store.generate_key("integration", str(uuid.uuid4()), 1)
    data = b"qmind-s3-integration"
    ctype = "text/plain"
    upload = store.presign_upload(key, content_type=ctype, max_bytes=1024, expires_in=300)
    import urllib.request

    req = urllib.request.Request(
        upload.url, data=data, method="PUT", headers=dict(upload.headers)
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status in (200, 204)

    head = store.head(key)
    assert head.exists
    assert head.content_length == len(data)
    assert store.get_bytes(key) == data
    assert store.presign_download(key, expires_in=60).startswith("http")
    store.delete(key)
    assert not store.head(key).exists
