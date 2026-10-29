#!/usr/bin/env python3
import re
from collections import Counter, defaultdict
from datetime import datetime

pat = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)[^"]*" (?P<status>\d+)'
)

def parse_ts(s):
    return datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z")

by_day = defaultdict(Counter)
manut = []
rootish = []
api_app = []

for line in open("/tmp/school-access-audit/raw.txt", encoding="utf-8", errors="replace"):
    m = pat.search(line)
    if not m:
        continue
    ts = parse_ts(m.group("ts"))
    day = ts.strftime("%Y-%m-%d")
    pth = m.group("path").split("?")[0]
    st = m.group("status")
    ip = m.group("ip")
    key = pth if pth in ("/", "/manutencao", "/acesso", "/api/health") else (
        "api:" + pth.split("/")[2] if pth.startswith("/api/") and len(pth.split("/")) > 2 else "other"
    )
    by_day[day][key] += 1
    if pth == "/manutencao":
        manut.append((ts, ip, st))
    if pth in ("/", "/acesso") or pth.startswith(("/secretaria", "/equipe", "/editor", "/roteiro", "/market")):
        rootish.append((ts, ip, st, pth))
    if any(pth.startswith(x) for x in (
        "/api/secretaria", "/api/pedagogico", "/api/equipe", "/api/auth/login", "/api/auth/me"
    )):
        api_app.append((ts, ip, st, pth))

print("=== hits by day (coarse) ===")
for d in sorted(by_day):
    print(d, dict(by_day[d]))

print("\n=== /manutencao hits ===")
print("count", len(manut))
for row in manut[:5]:
    print(" first", row[0].isoformat(), row[1], row[2])
for row in manut[-5:]:
    print(" last ", row[0].isoformat(), row[1], row[2])

print("\n=== document routes ===")
print("count", len(rootish))
for row in rootish:
    print(row[0].isoformat(), row[1], row[2], row[3])

print("\n=== app API unlocked evidence ===")
print("count", len(api_app))
for row in api_app:
    print(row[0].isoformat(), row[1], row[2], row[3])

print("\n=== IPs with app API ===")
print(Counter(r[1] for r in api_app))

# First api_app after lock file birth
birth = datetime.fromisoformat("2026-08-13T21:13:33+00:00")
after = [r for r in api_app if r[0] >= birth]
print("\napp API after lock-file birth", len(after))
if after:
    print("first after birth", after[0])
    print("last after birth", after[-1])
