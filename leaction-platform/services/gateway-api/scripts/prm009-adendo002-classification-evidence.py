from pathlib import Path
import subprocess

env = {}
for line in Path("/var/www/leaction-platform/.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        env[key] = value
url = env["DATABASE_URL"]


def q(sql):
    return subprocess.check_output(["psql", url, "-tAc", sql], text=True).strip()


print("loja_payload_keys=")
print(
    q(
        "select k from public.orders o "
        "cross join lateral jsonb_object_keys(o.external_resource_id::jsonb) as k "
        "where o.external_resource_id::jsonb->>'app_id' = 'lojadepaes' "
        "group by k order by k"
    )
)
print(
    "loja_live_mode="
    + q(
        "select flag || '=' || n::text from ("
        "select coalesce(external_resource_id::jsonb->>'live_mode','absent') as flag, count(*) as n "
        "from public.orders where external_resource_id::jsonb->>'app_id' = 'lojadepaes' group by 1) s"
    )
)
print(
    "loja_sandbox="
    + q(
        "select flag || '=' || n::text from ("
        "select coalesce(external_resource_id::jsonb->>'sandbox','absent') as flag, count(*) as n "
        "from public.orders where external_resource_id::jsonb->>'app_id' = 'lojadepaes' group by 1) s"
    )
)
print(
    "loja_test_order="
    + q(
        "select flag || '=' || n::text from ("
        "select coalesce(external_resource_id::jsonb->>'test_order','absent') as flag, count(*) as n "
        "from public.orders where external_resource_id::jsonb->>'app_id' = 'lojadepaes' group by 1) s"
    )
)
print("mp_token_prefix_not_queried=1")
print("public_orders=" + q("select count(*) from public.orders"))
print("isolated_orders=" + q("select count(*) from prm009_public_test.orders"))
