import json
import re
from pathlib import Path

ev = Path(__file__).resolve().parent
text = (ev / "ops-ecs-snap-pre2.out.txt").read_text(encoding="utf-8", errors="replace")
m = re.search(r"SNAPSHOT_JSON_BEGIN\n(\{.*?\})\nSNAPSHOT_JSON_END", text, re.S)
if not m:
    raise SystemExit("cannot restore pre from ops-ecs-snap-pre2.out.txt")
blob = json.loads(m.group(1))
(ev / "panne-demo-counts-pre.json").write_text(
    json.dumps(blob["demo"], ensure_ascii=False, indent=2), encoding="utf-8"
)
(ev / "panne-prod-intact-pre.json").write_text(
    json.dumps(blob["panne_intact"], ensure_ascii=False, indent=2), encoding="utf-8"
)
print("restored_pre_ok")
