from pathlib import Path

import pytest
from app.core.config import Settings
from app.domain.errors import ProductError
from app.domain.media_storage import LocalMediaStorage, media_storage


def test_local_storage_roundtrip(tmp_path: Path) -> None:
    storage = LocalMediaStorage(root=tmp_path)
    storage.put("abc.jpg", b"hello", "image/jpeg")
    assert storage.exists("abc.jpg")
    assert storage.open_bytes("abc.jpg") == b"hello"
    assert storage.local_path("abc.jpg") == tmp_path / "abc.jpg"


def test_s3_backend_requires_bucket() -> None:
    settings = Settings(media_backend="s3", media_s3_bucket="", media_s3_region="")
    with pytest.raises(ProductError, match="bucket"):
        media_storage(settings)
