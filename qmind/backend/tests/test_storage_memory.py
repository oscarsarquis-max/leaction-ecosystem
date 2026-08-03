"""Unit tests for in-memory object storage adapter."""

from __future__ import annotations

from app.storage.memory import InMemoryObjectStorage


def test_presign_put_head_get_delete():
    store = InMemoryObjectStorage()
    key = store.generate_key("org-1", "ev-1", 1)
    assert key == "org/org-1/evidence/ev-1/v1"
    upload = store.presign_upload(
        key, content_type="text/plain", max_bytes=100, expires_in=60
    )
    assert upload.method == "PUT"
    assert "memory://upload/" in upload.url
    assert not store.head(key).exists

    store.put_test_object(key, b"hello", "text/plain")
    head = store.head(key)
    assert head.exists
    assert head.content_length == 5
    assert head.content_type == "text/plain"
    assert store.get_bytes(key) == b"hello"
    assert "memory://download/" in store.presign_download(key, expires_in=30)
    store.delete(key)
    assert not store.head(key).exists
