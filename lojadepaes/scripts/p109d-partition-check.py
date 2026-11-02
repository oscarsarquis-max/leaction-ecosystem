"""109D: confere que as lentes de partição somam o total ("Todos") no banco apontado.

Somente leitura. Uso (captura local):
    python scripts/p109d-partition-check.py
Em produção roda dentro do contêiner da API (sem imprimir dados pessoais):
    docker compose exec -T -w /app/backend api python - < scripts/p109d-partition-check.py
Imprime só contagens e, se a soma não fechar, as referências sobrando (referência pública
do pedido ou id da solicitação de data; nunca nome, e-mail ou texto de cliente).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for candidate in (BACKEND, Path("/app/backend")):
    if candidate.exists():
        sys.path.insert(0, str(candidate))
        break

if not os.environ.get("LOJADEPAES_DATABASE_URL") and "--local" in sys.argv:
    os.environ["LOJADEPAES_DATABASE_URL"] = (
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
    )
if not os.environ.get("LOJADEPAES_DATABASE_URL") and not Path("/app/backend").exists():
    os.environ["LOJADEPAES_DATABASE_URL"] = (
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
    )

from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.domain.attendance import attendance_summary, list_attendance  # noqa: E402
from app.schemas.admin import OrderListQuery  # noqa: E402


def _all_items(session: Session, settings, lens: str) -> list:
    items: list = []
    page = 1
    while True:
        out = list_attendance(session, settings, OrderListQuery(lens=lens, page=page, page_size=50))
        items.extend(out.items)
        if len(items) >= out.total or not out.items:
            return items
        page += 1


def _key(item) -> str:
    return getattr(item, "row_key", None) or str(item.id)


def main() -> int:
    settings = get_settings()
    with Session(get_engine()) as session:
        summary = attendance_summary(session, settings)
        lenses = {row["key"]: row for row in summary["queue_lenses"]}
        partition = [row for row in summary["queue_lenses"] if row.get("partition")]
        total = lenses["all"]["count"]
        soma = sum(row["count"] for row in partition)
        for row in summary["queue_lenses"]:
            print(f"{row['key']:<22} {row['count']:>4}  grupo={row.get('group')} particao={bool(row.get('partition'))}")
        print(f"soma da particao = {soma}; Todos = {total}; historico = {lenses['history:all']['count']}")
        if soma == total:
            print("PARTICAO FECHA")
            return 0
        seen: dict[str, str] = {}
        for row in partition:
            for item in _all_items(session, settings, row["key"]):
                seen.setdefault(_key(item), row["key"])
        extra = [
            f"{item.public_reference} ({item.visible_stage})"
            for item in _all_items(session, settings, "all")
            if _key(item) not in seen
        ]
        print("SOBRANDO:", ", ".join(extra) or "(nenhum item identificado)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
