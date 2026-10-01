"""Patch live Monitor OIDC Edge to return 401 JSON on API without session."""

from __future__ import annotations

import io
import json
import subprocess
import zipfile
from pathlib import Path

REGION = "us-east-1"
FUNCTION = "spider-sandbox-monitor-oidc"
DIST = "E2E4ORTD4DHI1D"


def aws(args: list[str]) -> bytes:
    return subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])


def aws_json(args: list[str]) -> dict:
    raw = aws(args)
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("utf-16"))


def main() -> None:
    fn = aws_json(["lambda", "get-function", "--function-name", FUNCTION])
    url = fn["Code"]["Location"]
    raw = subprocess.check_output(["curl.exe", "-sS", url])
    zin = zipfile.ZipFile(io.BytesIO(raw))
    names = zin.namelist()
    source_name = next(name for name in names if name.endswith("index.js") or name == "index.js")
    text = zin.read(source_name).decode("utf-8")
    if "Unauthorized" in text and "application/problem+json" in text:
        print("edge_already_patched")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    old_is = (
        f"function isConsolePath(uri) {{{nl}"
        f"  return uri.indexOf(\"/v1/console\") === 0;{nl}"
        "}"
    )
    new_is = (
        f"function isConsolePath(uri) {{{nl}"
        f"  return uri.indexOf(\"/v1/console\") === 0 || uri.indexOf(\"/v1/canonical\") === 0;{nl}"
        f"}}{nl}"
        f"{nl}"
        f"function unauthorizedApi() {{{nl}"
        f"  return response({nl}"
        f"    401,{nl}"
        f"    null,{nl}"
        f"    [clearCookie(COOKIE_STATE)],{nl}"
        f"    JSON.stringify({{{nl}"
        f"      title: \"Unauthorized\",{nl}"
        f"      status: 401,{nl}"
        f"      detail: \"A sessao do Monitor e obrigatoria para consultar a engine.\",{nl}"
        f"    }}),{nl}"
        f"    \"application/problem+json\",{nl}"
        f"  );{nl}"
        "}"
    )
    if old_is not in text:
        raise SystemExit("isConsolePath block not found")
    text = text.replace(old_is, new_is, 1)
    text = text.replace(
        'status === 302 ? "Found" : status === 301 ? "Moved Permanently" : status === 403 ? "Forbidden" : "OK"',
        'status === 302 ? "Found" : status === 301 ? "Moved Permanently" : status === 403 ? "Forbidden" : status === 401 ? "Unauthorized" : "OK"',
        1,
    )
    old_req = (
        f"  const token = cookies[COOKIE_ID];{nl}"
        f"  if (!token) {{{nl}"
        f"    logEvent(\"auth_failure\", \"anonymous\");{nl}"
        f"    return authorizeRedirect(request.uri);{nl}"
        "  }"
    )
    new_req = (
        f"  const token = cookies[COOKIE_ID];{nl}"
        f"  const uri = request.uri.split(\"?\")[0];{nl}"
        f"  if (!token) {{{nl}"
        f"    logEvent(\"auth_failure\", \"anonymous\");{nl}"
        f"    return isConsolePath(uri) ? unauthorizedApi() : authorizeRedirect(request.uri);{nl}"
        "  }"
    )
    if old_req not in text:
        raise SystemExit("requireSession anonymous block not found")
    text = text.replace(old_req, new_req, 1)
    text = text.replace(
        f"    return authorizeRedirect(request.uri);{nl}  }}{nl}}}{nl}{nl}async function handle(event)",
        f"    return isConsolePath(uri) ? unauthorizedApi() : authorizeRedirect(request.uri);{nl}  }}{nl}}}{nl}{nl}async function handle(event)",
        1,
    )
    if "exports._internal" in text and "isConsolePath," not in text:
        text = text.replace("  CONFIG,\n  safeReturnTo,", "  CONFIG,\n  isConsolePath,\n  safeReturnTo,", 1)
    out = Path.home() / "AppData" / "Local" / "Temp" / "prm009-inc001-edge.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            data = text.encode("utf-8") if name == source_name else zin.read(name)
            zout.writestr(name, data)
    out.write_bytes(buf.getvalue())
    aws_json(["lambda", "update-function-code", "--function-name", FUNCTION, "--zip-file", f"fileb://{out}"])
    subprocess.check_call(["aws", "lambda", "wait", "function-updated", "--function-name", FUNCTION, "--region", REGION])
    published = aws_json(["lambda", "publish-version", "--function-name", FUNCTION, "--description", "prm009-inc001-api-401"])
    version = published["Version"]
    new_arn = published["FunctionArn"]
    print(f"edge_version={version}")
    cfg = aws_json(["cloudfront", "get-distribution-config", "--id", DIST])
    etag = cfg["ETag"]
    dist = cfg["DistributionConfig"]

    def bump(assoc: dict) -> None:
        items = assoc.get("Items") or []
        for item in items:
            arn = item.get("LambdaFunctionARN") or ""
            if FUNCTION in arn:
                item["LambdaFunctionARN"] = new_arn

    bump(dist["DefaultCacheBehavior"].get("LambdaFunctionAssociations") or {})
    for behavior in (dist.get("CacheBehaviors") or {}).get("Items") or []:
        bump(behavior.get("LambdaFunctionAssociations") or {})
    path = Path.home() / "AppData" / "Local" / "Temp" / "prm009-inc001-cf.json"
    path.write_text(json.dumps({"DistributionConfig": dist, "Id": DIST, "IfMatch": etag}), encoding="utf-8")
    # CloudFront update uses separate flags
    path_cfg = Path.home() / "AppData" / "Local" / "Temp" / "prm009-inc001-cf-dist.json"
    path_cfg.write_text(json.dumps(dist), encoding="utf-8")
    subprocess.check_call(
        [
            "aws",
            "cloudfront",
            "update-distribution",
            "--id",
            DIST,
            "--if-match",
            etag,
            "--distribution-config",
            f"file://{path_cfg}",
            "--region",
            "us-east-1",
        ]
    )
    print("cloudfront_updated")
    out.unlink(missing_ok=True)
    path.unlink(missing_ok=True)
    path_cfg.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
