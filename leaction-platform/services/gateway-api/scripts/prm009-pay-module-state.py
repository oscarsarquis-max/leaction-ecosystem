from pathlib import Path
import subprocess

env = {}
for line in Path("/var/www/leaction-platform/.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        env[key] = value
url = env["DATABASE_URL"]


def q(sql):
    try:
        return subprocess.check_output(
            ["psql", url, "-tAc", sql],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as error:
        detail = (error.output or "").replace(url, "[redacted]")
        raise SystemExit("psql_failed " + detail[-400:])


print("amount_checkout_apps=" + str(env.get("AMOUNT_CHECKOUT_APP_IDS")))
print("lookup_enabled=" + str(env.get("ACTIONHUB_PAY_LOOKUP_ENABLED")))
print("lookup_operational=" + str(env.get("ACTIONHUB_PAY_LOOKUP_OPERATIONAL")))
print("operational_apps=" + str(env.get("ACTIONHUB_PAY_OPERATIONAL_APP_IDS")))
print("mp_notification_url_set=" + str(bool((env.get("MP_NOTIFICATION_URL") or "").strip())))
print("mp_token_prefix=" + ("TEST" if str(env.get("MP_ACCESS_TOKEN") or "").startswith("TEST-") else "LIVE_OR_OTHER" if env.get("MP_ACCESS_TOKEN") else "ABSENT"))

print("orders_by_app_method_status=")
print(
    q(
        """
        select app || '|' || method || '|' || st || '|n=' || n::text
        from (
          select coalesce(nullif(o.external_resource_id::jsonb->>'app_id',''), '?') as app,
                 coalesce(nullif(o.external_resource_id::jsonb->>'method',''), '?') as method,
                 coalesce(upper(o.status),'?') as st,
                 count(*) as n
          from public.orders o
          group by 1,2,3
        ) s
        order by app, method, st
        """
    )
)

print("loja_amount_fields=")
print(
    q(
        """
        select
          'n=' || count(*)::text
          || '|amount_cents=' || count(*) filter (where (external_resource_id::jsonb->>'amount_cents') is not null)::text
          || '|paid_amount_cents=' || count(*) filter (where (external_resource_id::jsonb->>'paid_amount_cents') is not null)::text
          || '|mp_payment_id=' || count(*) filter (where (external_resource_id::jsonb->>'mp_payment_id') is not null)::text
          || '|pix_obj=' || count(*) filter (where external_resource_id::jsonb ? 'pix')::text
          || '|paid_at=' || count(*) filter (where paid_at is not null)::text
          || '|gateway_reference=' || count(*) filter (where gateway_reference is not null and gateway_reference <> '')::text
        from public.orders
        where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
        """
    )
)

print("loja_pix_vs_order=")
print(
    q(
        """
        select coalesce(upper(status),'?') || '|pix_status=' || coalesce(external_resource_id::jsonb->'pix'->>'status','absent')
          || '|n=' || count(*)::text
        from public.orders
        where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
        group by 1, 2
        order by 1, 2
        """
    )
)

print("loja_source=")
print(
    q(
        """
        select coalesce(external_resource_id::jsonb->>'source','absent') || '=' || count(*)::text
        from public.orders
        where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
        group by 1
        """
    )
)

print("amount_outbox=")
print(
    q(
        """
        select coalesce(event_type,'?') || '|' || coalesce(status,'?') || '=' || count(*)::text
        from webhook_outbox
        where app_id = 'lojadepaes'
           or idempotency_key like 'amount_%'
        group by 1, 2
        order by 1, 2
        """
    )
)

print("public_orders=" + q("select count(*) from public.orders"))
print("isolated_orders=" + q("select count(*) from prm009_public_test.orders"))
print("products_amount=" + q("select count(*) from products where sku = 'AMOUNT_CHECKOUT' or type = 'AMOUNT_CHECKOUT'"))
