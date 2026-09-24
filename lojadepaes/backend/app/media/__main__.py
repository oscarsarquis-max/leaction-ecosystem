from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.media_storage import media_storage
from app.models.products import MediaAsset


def migrate_local(delete_source: bool = False) -> int:
    settings = get_settings()
    source = media_storage(settings, "local")
    target = media_storage(settings)
    if target.backend_name == "local":
        print("destino ainda é local; nada a copiar")
        return 0
    session = Session(get_engine())
    copied = 0
    try:
        rows = session.scalars(select(MediaAsset)).all()
        for asset in rows:
            key = asset.object_key or asset.stored_name
            if asset.storage_backend == target.backend_name and target.exists(key):
                continue
            payload = source.open_bytes(key)
            target.put(key, payload, asset.content_type)
            if len(target.open_bytes(key)) != asset.byte_size:
                raise RuntimeError(f"tamanho divergente após copiar {key}")
            asset.storage_backend = target.backend_name
            asset.object_key = key
            copied += 1
        session.commit()
    finally:
        session.close()
    if delete_source:
        print("exclusão automática dos originais não é feita; copie e confira antes de apagar")
    print(f"referências atualizadas: {copied}")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Copia mídias locais para o backend configurado")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("uso: python -m app.media --apply")
        return
    migrate_local()


if __name__ == "__main__":
    main()
