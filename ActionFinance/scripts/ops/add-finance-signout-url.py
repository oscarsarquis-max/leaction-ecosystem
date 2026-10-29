"""Add one exact Finance Allowed sign-out URL. Never prints secrets."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REGION = "us-east-2"
POOL_ID = "us-east-2_GYIa11WvX"
CLIENT_ID = "275ig9d7lfi0j7if9rqe374rqc"
CLIENT_NAME = "actionfinance-confidential"
ADDED = "https://actionfinance.actionhub.com.br/oauth2/authorization/actionfinance"
COPY = (
    "ClientName",
    "RefreshTokenValidity",
    "AccessTokenValidity",
    "IdTokenValidity",
    "TokenValidityUnits",
    "ReadAttributes",
    "WriteAttributes",
    "ExplicitAuthFlows",
    "SupportedIdentityProviders",
    "CallbackURLs",
    "AllowedOAuthFlows",
    "AllowedOAuthScopes",
    "AllowedOAuthFlowsUserPoolClient",
    "PreventUserExistenceErrors",
    "EnableTokenRevocation",
    "EnablePropagateAdditionalUserContextData",
    "AuthSessionValidity",
)


def aws_json(args: list[str]) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))
    return json.loads(raw.decode("utf-8"))


def public_view(client: dict) -> dict:
    return {
        "ClientName": client.get("ClientName"),
        "CallbackURLs": client.get("CallbackURLs"),
        "LogoutURLs": client.get("LogoutURLs"),
        "AllowedOAuthFlows": client.get("AllowedOAuthFlows"),
        "AllowedOAuthScopes": client.get("AllowedOAuthScopes"),
    }


def main() -> int:
    apply = "--apply" in sys.argv
    current = aws_json(
        ["cognito-idp", "describe-user-pool-client", "--user-pool-id", POOL_ID, "--client-id", CLIENT_ID]
    )["UserPoolClient"]
    if current.get("ClientName") != CLIENT_NAME or current.get("ClientId") != CLIENT_ID:
        print("refusing unexpected client")
        return 2
    snapshot = (
        pathlib.Path(__file__).resolve().parents[2]
        / "ops"
        / "aws"
        / "cognito-hosted-ui"
        / "logout-urls-before-010.json"
    )
    snapshot.write_text(json.dumps(public_view(current), indent=2) + "\n", encoding="utf-8")
    logout = list(current.get("LogoutURLs") or [])
    next_logout = list(logout)
    if ADDED not in next_logout:
        next_logout.append(ADDED)
    print(json.dumps({"snapshot": str(snapshot), "currentLogout": logout, "nextLogout": next_logout, "apply": apply}))
    if not apply or next_logout == logout:
        return 0
    body = {"UserPoolId": POOL_ID, "ClientId": CLIENT_ID, "LogoutURLs": next_logout}
    for key in COPY:
        if key in current and current[key] is not None:
            body[key] = current[key]
    path = pathlib.Path(os.environ["TEMP"]) / "af-signout-url.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    try:
        aws_json(["cognito-idp", "update-user-pool-client", "--cli-input-json", f"file://{path}"])
    finally:
        if path.exists():
            path.unlink()
    after = aws_json(
        ["cognito-idp", "describe-user-pool-client", "--user-pool-id", POOL_ID, "--client-id", CLIENT_ID]
    )["UserPoolClient"]
    print(json.dumps({"updated": public_view(after)}))
    if after.get("CallbackURLs") != current.get("CallbackURLs"):
        print("callback urls changed unexpectedly")
        return 3
    if ADDED not in (after.get("LogoutURLs") or []):
        print("added sign-out url missing")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
