from pathlib import Path

hub = Path("/var/www/leaction-platform/.env")
school = Path("/var/www/inove4us-school/.env")


def keys(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.split("=", 1)
            data[key.strip()] = val
    return data


h = keys(hub)
s = keys(school)
if h.get("PRODUCTION_MASTER_KEY") and not s.get("PRODUCTION_MASTER_KEY"):
    with school.open("a", encoding="utf-8") as fh:
        fh.write("PRODUCTION_MASTER_KEY=" + h["PRODUCTION_MASTER_KEY"] + "\n")
    s = keys(school)
    print("school PRODUCTION_MASTER_KEY copied from hub")

for label, data in (("school", s), ("hub", h)):
    for key in (
        "SCHOOL_INTEGRATION_API_KEY",
        "SCHOOL_B2C_SHARED_SECRET",
        "INOVE4US_B2C_API_URL",
        "INOVE4US_B2C_WEBHOOK_URL",
        "SCHOOL_SYSTEM_LOCKED",
        "PRODUCTION_MASTER_KEY",
    ):
        val = data.get(key, "")
        print(label, key, "present" if str(val).strip() else "MISSING")

print(
    "keys_match",
    s.get("SCHOOL_INTEGRATION_API_KEY") == h.get("SCHOOL_INTEGRATION_API_KEY")
    and s.get("SCHOOL_B2C_SHARED_SECRET") == h.get("SCHOOL_B2C_SHARED_SECRET"),
)
