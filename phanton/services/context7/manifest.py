"""Manifest arquivo -> hash -> chunk_ids (JSON em CONTEXT7_INDEX_DIR)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class FileManifestEntry:
    content_hash: str
    chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"hash": self.content_hash, "chunk_ids": list(self.chunk_ids)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileManifestEntry":
        return cls(
            content_hash=str(data.get("hash") or data.get("content_hash") or ""),
            chunk_ids=[str(x) for x in (data.get("chunk_ids") or [])],
        )


class IndexManifest:
    """Mapa relativo de arquivos indexados, persistido em manifest.json."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.entries: dict[str, FileManifestEntry] = {}
        self.embedding_model: Optional[str] = None
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.entries = {}
            self.embedding_model = None
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.entries = {}
            self.embedding_model = None
            return
        if not isinstance(raw, dict):
            self.entries = {}
            self.embedding_model = None
            return
        self.embedding_model = (
            str(raw["embedding_model"]).strip()
            if raw.get("embedding_model")
            else None
        )
        files = raw.get("files")
        if not isinstance(files, dict):
            self.entries = {}
            return
        self.entries = {
            str(k).replace("\\", "/"): FileManifestEntry.from_dict(v)
            for k, v in files.items()
            if isinstance(v, dict)
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "embedding_model": self.embedding_model,
            "files": {k: v.to_dict() for k, v in sorted(self.entries.items())},
        }
        tmp = self.path.with_suffix(".json.tmp")
        with self._lock:
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)

    def clear_files(self) -> None:
        self.entries = {}

    def get(self, rel_path: str) -> FileManifestEntry | None:
        return self.entries.get(rel_path.replace("\\", "/"))

    def set(self, rel_path: str, entry: FileManifestEntry) -> None:
        self.entries[rel_path.replace("\\", "/")] = entry

    def pop(self, rel_path: str) -> FileManifestEntry | None:
        return self.entries.pop(rel_path.replace("\\", "/"), None)

    def paths(self) -> set[str]:
        return set(self.entries.keys())
