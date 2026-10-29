from pathlib import Path
import json
import urllib.error
import urllib.request

env = {}
for line in Path("/var/www/leaction-platform/.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        env[key] = value
secret = env["ACTIONHUB_PAY_PROVIDER_SECRET"]


def post(app, environment, company):
    payload = json.dumps(
        {
            "contractVersion": "1.4",
            "requestId": "adendo002",
            "correlationId": "adendo002",
            "capabilityId": "LIST_PAYMENT_TRANSACTIONS",
            "inputs": {
                "payAppId": app,
                "companyId": company,
                "environment": environment,
                "limit": 50,
            },
        }
    ).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:4001/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-ActionHub-Pay-Credential": secret,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode())
            result = body.get("result") or {}
            items = result.get("items") or []
            reviews = result.get("reviews") or []
            statuses = {}
            classes = {}
            review_classes = {}
            review_statuses = {}
            for item in items:
                statuses[item.get("originalStatus") or "?"] = statuses.get(item.get("originalStatus") or "?", 0) + 1
                classes[item.get("classification") or "?"] = classes.get(item.get("classification") or "?", 0) + 1
            for item in reviews:
                review_classes[item.get("classification") or "?"] = (
                    review_classes.get(item.get("classification") or "?", 0) + 1
                )
                review_statuses[item.get("originalStatus") or "?"] = (
                    review_statuses.get(item.get("originalStatus") or "?", 0) + 1
                )
            print(
                app,
                environment,
                response.status,
                "count=" + str(result.get("itemCount")),
                "reviewCount=" + str(result.get("reviewCount", len(reviews))),
                "status=" + ",".join(f"{k}={v}" for k, v in sorted(statuses.items())),
                "class=" + ",".join(f"{k}={v}" for k, v in sorted(classes.items())),
                "reviewClass=" + ",".join(f"{k}={v}" for k, v in sorted(review_classes.items())),
                "reviewStatus=" + ",".join(f"{k}={v}" for k, v in sorted(review_statuses.items())),
                "relation=public.orders" if app == "lojadepaes" else "relation=isolated-or-empty",
            )
    except urllib.error.HTTPError as error:
        print(app, environment, error.code)


post("lojadepaes", "PRODUCTION", "624023a4-57e3-415c-b7d0-925ca1acd3b7")
post("lojadepaes", "HOMOLOG", "624023a4-57e3-415c-b7d0-925ca1acd3b7")
post("af-public-test-padaria", "HOMOLOG", "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c")
post("inove4us", "PRODUCTION", "00000000-0000-0000-0000-000000000000")
print("isolated_untouched=4")
