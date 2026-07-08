"""Aplica patches PanelDX no banco leaction_hub (local)."""
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
HUB_ROOT = ROOT.parent / "leaction-platform"
if not HUB_ROOT.exists():
    HUB_ROOT = Path(r"C:\Projetos\leaction-platform")

PATCHES = [
    HUB_ROOT / "shared" / "database" / "patch_paneldx_vitrine_snapshot.sql",
    HUB_ROOT / "shared" / "database" / "patch_paneldx_subscription.sql",
]

db_url = os.environ.get(
    "HUB_DATABASE_URL",
    "postgresql://admin:password123@localhost:5433/leaction_hub",
)

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

for patch in PATCHES:
    if not patch.exists():
        print(f"SKIP missing {patch}")
        continue
    print(f"Applying {patch.name}...")
    cur.execute(patch.read_text(encoding="utf-8"))

cur.execute(
    "SELECT sku FROM products WHERE sku IN ('PANELDX_SUBSCRIPTION', 'PANEL_MATURIDADE')"
)
print("Products:", [r[0] for r in cur.fetchall()])

cur.execute(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'paneldx_vitrine_snapshots'
    """
)
print("paneldx_vitrine_snapshots:", "ok" if cur.fetchone() else "missing")

cur.close()
conn.close()
print("Hub DB patches applied.")
