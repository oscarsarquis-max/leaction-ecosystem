import json
import urllib.error
import urllib.request
from pathlib import Path

env = {}
for line in Path("/var/www/leaction-platform/.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        env[key] = value
secret = env["ACTIONHUB_PAY_PROVIDER_SECRET"]


def call(app):
    req = urllib.request.Request(
        "http://127.0.0.1:4001/v1/integration/payments?environment=HOMOLOG&limit=10"
    )
    req.add_header("X-Spider-Provider-Key", secret)
    req.add_header("X-Pay-App-Id", app)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode())
            print(
                app,
                response.status,
                "count=" + str(body.get("itemCount")),
                "test=" + str(body.get("testLabeled")),
                "env=" + str(body.get("environment")),
            )
    except urllib.error.HTTPError as error:
        print(app, error.code)


call("af-public-test-padaria")
call("loja-de-paes")

import subprocess

url = env["DATABASE_URL"]
public_count = subprocess.check_output(
    ["psql", url, "-tAc", "select count(*) from public.orders"], text=True
).strip()
isolated_count = subprocess.check_output(
    ["psql", url, "-tAc", "select count(*) from prm009_public_test.orders"], text=True
).strip()
print("public_orders=" + public_count)
print("isolated_orders=" + isolated_count)
