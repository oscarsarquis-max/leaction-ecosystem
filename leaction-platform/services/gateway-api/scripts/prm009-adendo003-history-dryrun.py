"""PRM_009 ADENDO_003 — dry-run histórico item a item. Sem APPLY, fulfill ou outbox."""
from pathlib import Path
import json
import os
import subprocess
import urllib.error
import urllib.request

RESTRICTED = Path("/var/www/leaction-platform/.dev-logs/prm009-adendo003-history-dryrun.json")
ENV_PATH = Path("/var/www/leaction-platform/.env")

env = {}
for line in ENV_PATH.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        env[key] = value
url = env["DATABASE_URL"]
mp_token = env.get("MP_ACCESS_TOKEN") or env.get("MERCADOPAGO_ACCESS_TOKEN") or ""


def q(sql):
    try:
        return subprocess.check_output(
            ["psql", url, "-tAc", sql],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as error:
        raise SystemExit("psql_failed " + (error.output or "").replace(url, "[redacted]")[-400:])


def mp_cents(amount):
    if amount is None:
        return None
    return int(round(float(amount) * 100))


def last4(value):
    text = "" if value is None else str(value)
    if not text:
        return None
    return text[-4:]


def mp_get(payment_id):
    if not mp_token or not payment_id:
        return {"ok": False, "reason": "sem_token_ou_referencia"}
    request = urllib.request.Request(
        "https://api.mercadopago.com/v1/payments/" + payment_id,
        headers={"Authorization": "Bearer " + mp_token, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return {"ok": False, "reason": "http_" + str(error.code)}
    except Exception:
        return {"ok": False, "reason": "consulta_inconclusiva"}
    return {
        "ok": True,
        "status": body.get("status"),
        "status_detail": body.get("status_detail"),
        "live_mode": body.get("live_mode"),
        "captured": body.get("captured"),
        "currency": body.get("currency_id"),
        "transaction_amount": body.get("transaction_amount"),
        "observed_amount_cents": mp_cents(body.get("transaction_amount")),
        "collector_suffix": last4(body.get("collector_id")),
        "date_approved_present": body.get("date_approved") is not None,
        "date_created": body.get("date_created"),
        "date_last_updated": body.get("date_last_updated"),
        "paid_confirmed": (
            str(body.get("status") or "").lower() == "approved" and body.get("captured") is not False
        ),
    }


def map_mp(status):
    value = str(status or "").lower()
    if value == "approved":
        return "PAID"
    if value == "authorized":
        return "AUTHORIZED"
    if value in ("cancelled", "expired"):
        return "CANCELLED"
    if value in ("pending", "in_process", "in_mediation"):
        return "PENDING"
    if value == "rejected":
        return "FAILED"
    if not value:
        return None
    return value.upper()


rows = q(
    """
    select json_build_object(
      'id', o.id,
      'status', upper(o.status),
      'method', coalesce(o.external_resource_id::jsonb->>'method','?'),
      'amount_cents', o.external_resource_id::jsonb->>'amount_cents',
      'paid_amount_cents', o.external_resource_id::jsonb->>'paid_amount_cents',
      'paid_amount_confirmed', o.external_resource_id::jsonb->>'paid_amount_confirmed',
      'observed_amount_cents', o.external_resource_id::jsonb->>'observed_amount_cents',
      'pix_status', o.external_resource_id::jsonb->'pix'->>'status',
      'provider_status', o.external_resource_id::jsonb->>'provider_status',
      'live_mode', o.external_resource_id::jsonb->>'live_mode',
      'mp_payment_id_present', (o.external_resource_id::jsonb->>'mp_payment_id') is not null,
      'mp_payment_id', o.external_resource_id::jsonb->>'mp_payment_id',
      'paid_at_present', o.paid_at is not null,
      'created_at', o.created_at,
      'updated_at', o.updated_at,
      'provider_observed_at', o.external_resource_id::jsonb->>'provider_observed_at',
      'gateway_reference_present', coalesce(o.gateway_reference,'') <> '',
      'has_mismatch', o.external_resource_id::jsonb ? 'amount_mismatch'
    )
    from public.orders o
    where o.external_resource_id::jsonb->>'app_id' = 'lojadepaes'
    order by o.created_at
    """
)
items = [json.loads(line) for line in rows.splitlines() if line.strip()]
dry = []
for item in items:
    mp = mp_get(item.get("mp_payment_id")) if item.get("mp_payment_id_present") else {
        "ok": False,
        "reason": "pendente_sem_referencia",
    }
    hub_status = item.get("status")
    mp_status = mp.get("status") if mp.get("ok") else None
    mapped = map_mp(mp_status)
    charged = item.get("amount_cents")
    observed = mp.get("observed_amount_cents") if mp.get("ok") else None
    paid_confirmed = bool(mp.get("ok") and mp.get("paid_confirmed"))
    status_divergence = None
    if mp.get("ok") and mapped and hub_status and mapped != hub_status:
        status_divergence = "hub=" + str(hub_status) + " mp=" + str(mp_status) + " mapped=" + mapped
    elif not mp.get("ok"):
        status_divergence = "hub=" + str(hub_status) + " mp=sem_referencia_ou_inconclusivo"
    proposed = {
        "keep_amount_cents": charged,
        "keep_order_status": hub_status,
        "observed_amount_cents": str(observed) if observed is not None else None,
        "paid_amount_cents": str(observed) if paid_confirmed else None,
        "paid_amount_confirmed": paid_confirmed,
        "pix_status": mp_status or item.get("pix_status"),
        "live_mode": mp.get("live_mode") if mp.get("ok") else None,
        "destination_collector_suffix": mp.get("collector_suffix") if mp.get("ok") else None,
        "status_divergence": status_divergence,
        "apply_fulfill": False,
        "apply_outbox": False,
        "do_not_use_price_70": True,
        "source": "mp_payment.transaction_amount" if mp.get("ok") else "origem_hub_apenas",
        "reason": (
            "consulta_leitura_mp_pago_confirmado" if paid_confirmed
            else ("consulta_leitura_mp_observado_sem_pago" if mp.get("ok") else mp.get("reason"))
        ),
        "precondition_updated_at": item.get("updated_at"),
        "precondition_provider_observed_at": item.get("provider_observed_at"),
        "note_get_paid_can_write_observation": True,
    }
    dry.append({
        "id_suffix": str(item.get("id") or "")[-8:],
        "current": {k: v for k, v in item.items() if k != "mp_payment_id"},
        "mp_read": {k: v for k, v in mp.items() if k != "body"},
        "proposed": proposed,
    })

RESTRICTED.parent.mkdir(parents=True, exist_ok=True)
RESTRICTED.write_text(json.dumps({"count": len(dry), "items": dry, "apply": False}, ensure_ascii=True), encoding="utf-8")
os.chmod(RESTRICTED, 0o600)

print("count=" + str(len(dry)))
print("apply=false")
print("get_paid_can_write_observation=true")
print("restricted=" + str(RESTRICTED))
for row in dry:
    current = row["current"]
    proposed = row["proposed"]
    mp_read = row["mp_read"]
    print(
        "item suffix=" + row["id_suffix"]
        + " method=" + str(current.get("method"))
        + " hub_status=" + str(current.get("status"))
        + " mp_status=" + str(mp_read.get("status") or mp_read.get("reason"))
        + " charged=" + str(current.get("amount_cents"))
        + " observed=" + str(proposed.get("observed_amount_cents"))
        + " paid_proposed=" + str(proposed.get("paid_amount_cents"))
        + " paid_confirmed=" + str(proposed.get("paid_amount_confirmed")).lower()
        + " live_mode=" + str(proposed.get("live_mode"))
        + " dest=" + str(proposed.get("destination_collector_suffix"))
        + " divergence=" + str(proposed.get("status_divergence") or "none")
        + " updated_at_present=" + str(bool(current.get("updated_at"))).lower()
    )
