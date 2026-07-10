from pathlib import Path

env_path = Path("/opt/chamelleon/backend/.env")
frag_path = Path("/tmp/chamelleon-aws-fragment.env")
updates = {}
for line in frag_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    updates[key.strip()] = value.strip()

lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
seen = set()
out = []
for line in lines:
    key = line.split("=", 1)[0].strip() if "=" in line and not line.strip().startswith("#") else ""
    if key in updates:
        out.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")
env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
print("patched keys:", ", ".join(sorted(updates)))
