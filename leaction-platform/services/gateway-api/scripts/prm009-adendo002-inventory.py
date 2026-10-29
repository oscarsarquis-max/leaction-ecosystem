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


print("app_registry_cols=")
print(
    q(
        "select column_name from information_schema.columns "
        "where table_schema='public' and table_name='app_registry' order by ordinal_position"
    )
)
print("apps=")
print(q("select app_id from app_registry order by app_id"))
print("orders_by_app=")
print(
    q(
        """
        select app_key || '|total=' || n::text || '|sandbox=' || sandbox_n::text
          || '|test=' || test_n::text || '|neither=' || neither_n::text
        from (
          select coalesce(nullif(o.external_resource_id::jsonb->>'app_id',''), '?') as app_key,
                 count(*) as n,
                 count(*) filter (where (o.external_resource_id::jsonb->>'sandbox') = 'true') as sandbox_n,
                 count(*) filter (where (o.external_resource_id::jsonb->>'test_order') = 'true') as test_n,
                 count(*) filter (
                   where coalesce(o.external_resource_id::jsonb->>'sandbox','') <> 'true'
                     and coalesce(o.external_resource_id::jsonb->>'test_order','') <> 'true'
                 ) as neither_n
          from public.orders o
          group by coalesce(nullif(o.external_resource_id::jsonb->>'app_id',''), '?')
        ) s
        order by n desc
        """
    )
)
print("loja_status=")
print(
    q(
        """
        select st || '=' || n::text
        from (
          select coalesce(upper(status),'?') as st, count(*) as n
          from public.orders
          where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
          group by coalesce(upper(status),'?')
        ) s
        order by st
        """
    )
)
print("loja_ref_prefix=")
print(
    q(
        """
        select prefix || '=' || n::text
        from (
          select split_part(coalesce(gateway_ref,''), ':', 1) as prefix, count(*) as n
          from public.orders
          where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
          group by split_part(coalesce(gateway_ref,''), ':', 1)
        ) s
        """
    )
)
print("loja_payload_keys=")
print(
    q(
        """
        select k
        from public.orders o
        cross join lateral jsonb_object_keys(o.external_resource_id::jsonb) as k
        where o.external_resource_id::jsonb->>'app_id' = 'lojadepaes'
        group by k
        order by k
        """
    )
)
print("isolated_orders=" + q("select count(*) from prm009_public_test.orders"))
print("public_orders=" + q("select count(*) from public.orders"))
print("hub_ref_apps=")
print(
    q(
        """
        select split_part(gateway_ref, ':', 2) || '|n=' || count(*)::text
        from public.orders
        where gateway_ref like 'hub:%' or gateway_ref like 'amount:%'
        group by 1
        order by count(*) desc
        """
    )
)
print("public_orders=" + q("select count(*) from public.orders"))
print("isolated_orders=" + q("select count(*) from prm009_public_test.orders"))
print("lookup_enabled=" + str(env.get("ACTIONHUB_PAY_LOOKUP_ENABLED")))
print("lookup_isolated=" + str(env.get("ACTIONHUB_PAY_LOOKUP_ISOLATED")))
print("lookup_public_test=" + str(env.get("ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST")))
