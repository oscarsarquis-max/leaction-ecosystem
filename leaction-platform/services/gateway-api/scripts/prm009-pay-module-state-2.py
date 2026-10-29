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


print("loja_pix_vs_order=")
print(
    q(
        """
        select st || '|pix=' || pix || '|n=' || n::text
        from (
          select coalesce(upper(status),'?') as st,
                 coalesce(external_resource_id::jsonb->'pix'->>'status','absent') as pix,
                 count(*) as n
          from public.orders
          where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
          group by 1, 2
        ) s
        order by st, pix
        """
    )
)

print("outbox_loja=")
print(
    q(
        """
        select ev || '|' || st || '=' || n::text
        from (
          select coalesce(event_type,'?') as ev,
                 coalesce(status,'?') as st,
                 count(*) as n
          from webhook_outbox
          where app_id = 'lojadepaes'
          group by 1, 2
        ) s
        order by ev, st
        """
    )
)

print("outbox_amount_keys=")
print(
    q(
        """
        select count(*)::text
        from webhook_outbox
        where idempotency_key like 'amount_%'
        """
    )
)

print("orders_paid_at_null_when_paid=")
print(
    q(
        """
        select count(*)::text
        from public.orders
        where external_resource_id::jsonb->>'app_id' = 'lojadepaes'
          and upper(status) = 'PAID'
          and paid_at is null
        """
    )
)
